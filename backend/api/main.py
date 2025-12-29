import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from io import BytesIO

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.orchestrator import OrchestratorAgent
from agents.base import AgentMessage, MessageType
from services.data_loader import DataLoader
from models.constraints import Constraints


app = FastAPI(
    title="McDonald's Workforce Scheduling API",
    description="Multi-Agent Intelligent Scheduling System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5175",
        "http://localhost:3000",
        "https://frontend-j6a8a9f1b-duncansebampitako-7785s-projects.vercel.app",
        "https://frontend-iznanfkss-duncansebampitako-7785s-projects.vercel.app",
        "https://frontend-ow89ddqiz-duncansebampitako-7785s-projects.vercel.app",
        "https://frontend-geg5byqmk-duncansebampitako-7785s-projects.vercel.app",
        "https://frontend-ecru-nine-41.vercel.app",
        "https://frontend-duncansebampitako-7785s-projects.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow all Vercel deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = OrchestratorAgent()
# Data files are in project root (one level up from backend)
# On Render, root directory is 'backend', so go up one level
data_loader = DataLoader(data_dir=str(Path(__file__).parent.parent.parent))


class GenerateRosterRequest(BaseModel):
    store_id: Optional[str] = "suburban_store"
    start_date: Optional[str] = None  # YYYY-MM-DD
    weeks: int = 2
    time_limit_seconds: int = 180


class RosterResponse(BaseModel):
    status: str
    roster: List[Dict[str, Any]]
    days: List[str]
    total_employees: int
    generation_time_seconds: float
    workflow_log: List[Dict[str, Any]]
    conflicts: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    peak_coverage: Dict[str, Any] = {}
    demand_analysis: Dict[str, Any] = {}
    skill_matching: Dict[str, Any] = {}


@app.get("/")
async def root():
    return {
        "service": "McDonald's Workforce Scheduling API",
        "version": "1.0.0",
        "agents": [
            "OrchestratorAgent",
            "DemandAgent",
            "MatcherAgent",
            "ValidatorAgent",
            "ResolverAgent",
        ],
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/data")
async def get_loaded_data():
    """Get all loaded employee and store data."""
    try:
        data = data_loader.get_all_data()
        
        # Convert models to dicts
        stores = [s.model_dump() for s in data.get("stores", [])]
        employees = [e.model_dump() for e in data.get("employees", [])]
        managers = [m.model_dump() for m in data.get("managers", [])]
        
        return {
            "stores": stores,
            "employees": employees,
            "managers": managers,
            "total_employees": data.get("total_employees", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stores")
async def get_stores():
    """Get available store configurations."""
    try:
        stores = data_loader.parse_stores()
        return {"stores": [s.model_dump() for s in stores]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/employees")
async def get_employees():
    """Get all employees with availability."""
    try:
        employees = data_loader.parse_employees()
        managers = data_loader.parse_managers()
        all_employees = employees + managers
        return {
            "employees": [e.model_dump() for e in all_employees],
            "total": len(all_employees),
            "managers": len(managers),
            "crew": len(employees),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/constraints")
async def get_constraints():
    """Get scheduling constraints (Australian Fair Work Act)."""
    constraints = Constraints()
    return constraints.model_dump()


@app.post("/api/generate", response_model=RosterResponse)
async def generate_roster(request: GenerateRosterRequest):
    """Generate an optimized roster using multi-agent system."""
    try:
        # Load data
        data = data_loader.get_all_data()
        
        if not data.get("employees"):
            raise HTTPException(status_code=400, detail="No employee data loaded")
        
        # Get store configuration
        stores = data.get("stores", [])
        store = stores[0] if stores else None
        
        if not store:
            # Create default store
            from models.store import Store, StaffingRequirement, StoreType
            store = Store(
                store_id="default_store",
                location_type=StoreType.SUBURBAN,
                normal_requirements=StaffingRequirement(
                    kitchen_staff=3,
                    counter_staff=3,
                    mccafe_staff=1,
                ),
                peak_requirements=StaffingRequirement(
                    kitchen_staff=4,
                    counter_staff=4,
                    mccafe_staff=2,
                ),
            )
        
        # Generate days for roster
        if request.start_date:
            start = datetime.strptime(request.start_date, "%Y-%m-%d")
        else:
            # Start from next Monday
            today = datetime.now()
            days_ahead = 7 - today.weekday()
            start = today + timedelta(days=days_ahead)
        
        days = []
        for i in range(request.weeks * 7):
            day = start + timedelta(days=i)
            days.append(day.strftime("%Y-%m-%d"))
        
        # Convert employees to dicts
        employees_data = [e.model_dump() for e in data.get("employees", [])]
        store_data = store.model_dump()
        
        # Orchestrate roster generation
        message = AgentMessage(
            sender="API",
            recipient=orchestrator.name,
            message_type=MessageType.REQUEST,
            action="generate_roster",
            payload={
                "store": store_data,
                "employees": employees_data,
                "days": days,
                "time_limit_seconds": request.time_limit_seconds,
            },
        )
        
        result = orchestrator.process(message)
        payload = result.payload
        
        return RosterResponse(
            status=payload.get("status", "unknown"),
            roster=payload.get("roster", []),
            days=payload.get("days", days),
            total_employees=payload.get("total_employees", 0),
            generation_time_seconds=payload.get("generation_time_seconds", 0),
            workflow_log=payload.get("workflow_log", []),
            conflicts=payload.get("final_validation", {}).get("conflicts", []),
            warnings=payload.get("final_validation", {}).get("warnings", []),
            peak_coverage=payload.get("peak_coverage", {}),
            demand_analysis=payload.get("demand_analysis", {}),
            skill_matching=payload.get("skill_matching", {}),
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/validate")
async def validate_roster(roster: List[Dict[str, Any]], days: List[str]):
    """Validate an existing roster."""
    try:
        from agents.validator_agent import ValidatorAgent
        validator = ValidatorAgent()
        
        # Load store for validation
        data = data_loader.get_all_data()
        stores = data.get("stores", [])
        store = stores[0].model_dump() if stores else {}
        
        message = AgentMessage(
            sender="API",
            recipient=validator.name,
            message_type=MessageType.REQUEST,
            action="validate_roster",
            payload={
                "roster": roster,
                "days": days,
                "store": store,
            },
        )
        
        result = validator.process(message)
        return result.payload
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/resolve")
async def resolve_conflicts(conflicts: List[Dict[str, Any]], roster: List[Dict[str, Any]]):
    """Suggest resolutions for conflicts."""
    try:
        from agents.resolver_agent import ResolverAgent
        resolver = ResolverAgent()
        
        # Load employees for resolution suggestions
        data = data_loader.get_all_data()
        employees_data = [e.model_dump() for e in data.get("employees", [])]
        
        message = AgentMessage(
            sender="API",
            recipient=resolver.name,
            message_type=MessageType.REQUEST,
            action="resolve_conflicts",
            payload={
                "conflicts": conflicts,
                "roster": roster,
                "employees": employees_data,
            },
        )
        
        result = resolver.process(message)
        return result.payload
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export")
async def export_roster(start_date: Optional[str] = None, weeks: int = 2):
    """Generate and export roster to Excel."""
    try:
        # Generate roster first
        request = GenerateRosterRequest(start_date=start_date, weeks=weeks)
        roster_response = await generate_roster(request)
        
        # Create Excel file
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Sheet 1: Roster Overview
            roster_data = []
            for emp in roster_response.roster:
                row = {
                    "Employee ID": emp.get("employee_id"),
                    "Name": emp.get("employee_name"),
                    "Type": emp.get("employee_type"),
                    "Manager": "Yes" if emp.get("is_manager") else "No",
                    "Total Hours": emp.get("total_hours", 0),
                }
                # Add shifts for each day
                for day in roster_response.days:
                    shift_info = emp.get("shifts", {}).get(day, {})
                    row[day] = shift_info.get("shift_code", "/")
                roster_data.append(row)
            
            df_roster = pd.DataFrame(roster_data)
            df_roster.to_excel(writer, sheet_name="Roster", index=False)
            
            # Sheet 2: Conflicts
            if roster_response.conflicts:
                df_conflicts = pd.DataFrame(roster_response.conflicts)
                df_conflicts.to_excel(writer, sheet_name="Conflicts", index=False)
            
            # Sheet 3: Workflow Log
            if roster_response.workflow_log:
                df_log = pd.DataFrame(roster_response.workflow_log)
                df_log.to_excel(writer, sheet_name="Workflow Log", index=False)
        
        output.seek(0)
        
        filename = f"roster_{roster_response.days[0]}_{roster_response.days[-1]}.xlsx"
        
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents")
async def get_agent_states():
    """Get current state of all agents."""
    return {
        "orchestrator": orchestrator.get_state(),
        "demand": orchestrator.demand_agent.get_state(),
        "matcher": orchestrator.matcher_agent.get_state(),
        "validator": orchestrator.validator_agent.get_state(),
        "resolver": orchestrator.resolver_agent.get_state(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
