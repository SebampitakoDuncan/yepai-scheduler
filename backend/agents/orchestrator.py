import time
from typing import Dict, Any, List
from .base import BaseAgent, AgentMessage, MessageType
from .demand_agent import DemandAgent
from .matcher_agent import MatcherAgent
from .validator_agent import ValidatorAgent
from .resolver_agent import ResolverAgent
from services.scheduler import SchedulerService
from models.store import Store, StaffingRequirement, StoreType
from models.employee import Employee, EmployeeType, Station
from models.constraints import Constraints


class OrchestratorAgent(BaseAgent):
    """Master agent that coordinates the multi-agent scheduling system."""
    
    def __init__(self):
        super().__init__(name="OrchestratorAgent")
        
        # Initialize sub-agents
        self.demand_agent = DemandAgent()
        self.matcher_agent = MatcherAgent()
        self.validator_agent = ValidatorAgent()
        self.resolver_agent = ResolverAgent()
        
        # Workflow state
        self.workflow_log = []
    
    def process(self, message: AgentMessage) -> AgentMessage:
        """Process orchestration requests."""
        action = message.action
        payload = message.payload
        
        if action == "generate_roster":
            store_data = payload.get("store", {})
            employees_data = payload.get("employees", [])
            days = payload.get("days", [])
            time_limit = payload.get("time_limit_seconds", 180)
            
            result = self.orchestrate_roster_generation(
                store_data, employees_data, days, time_limit
            )
            
            return self.send_message(
                recipient=message.sender,
                action="roster_complete",
                payload=result,
                message_type=MessageType.RESPONSE,
                correlation_id=message.correlation_id,
            )
        
        return self.send_message(
            recipient=message.sender,
            action="error",
            payload={"error": f"Unknown action: {action}"},
            message_type=MessageType.ERROR,
        )
    
    def orchestrate_roster_generation(
        self,
        store_data: Dict[str, Any],
        employees_data: List[Dict[str, Any]],
        days: List[str],
        time_limit: int = 180,
    ) -> Dict[str, Any]:
        """Orchestrate the full roster generation workflow."""
        start_time = time.time()
        self.set_status("orchestrating")
        self.workflow_log = []
        
        self._log_step("INIT", "Starting roster generation workflow")
        
        # Step 1: Analyze demand with DemandAgent
        self._log_step("DEMAND", "Analyzing staffing demand patterns")
        demand_msg = AgentMessage(
            sender=self.name,
            recipient=self.demand_agent.name,
            message_type=MessageType.REQUEST,
            action="analyze_demand",
            payload={"store": store_data, "days": days},
        )
        demand_result = self.demand_agent.process(demand_msg)
        demand_analysis = demand_result.payload
        self._log_step("DEMAND", f"Completed: {len(days)} days analyzed")
        
        # Step 2: Match skills with MatcherAgent
        self._log_step("MATCH", "Matching employee skills to stations")
        
        # Get station requirements from store
        station_reqs = {}
        normal_reqs = store_data.get("normal_requirements", {})
        if isinstance(normal_reqs, dict):
            station_reqs = {
                "Kitchen": normal_reqs.get("kitchen_staff", 0),
                "Counter": normal_reqs.get("counter_staff", 0),
                "McCafe": normal_reqs.get("mccafe_staff", 0),
            }
        
        match_msg = AgentMessage(
            sender=self.name,
            recipient=self.matcher_agent.name,
            message_type=MessageType.REQUEST,
            action="match_skills",
            payload={
                "employees": employees_data,
                "station_requirements": station_reqs,
            },
        )
        match_result = self.matcher_agent.process(match_msg)
        skill_matching = match_result.payload
        self._log_step("MATCH", f"Completed: {len(employees_data)} employees matched")
        
        # Step 3: Generate roster with SchedulerService
        self._log_step("SCHEDULE", "Generating optimized roster with CSP solver")
        
        # Convert data to models
        store = self._convert_to_store(store_data)
        employees = self._convert_to_employees(employees_data)
        constraints = Constraints()
        
        scheduler = SchedulerService(
            employees=employees,
            store=store,
            constraints=constraints,
            days=days,
        )
        
        roster_result = scheduler.generate_roster(time_limit_seconds=time_limit)
        self._log_step("SCHEDULE", f"Completed in {roster_result.get('solve_time_seconds', 0)}s")
        
        # Step 4: Validate roster with ValidatorAgent
        self._log_step("VALIDATE", "Validating roster against constraints")
        validate_msg = AgentMessage(
            sender=self.name,
            recipient=self.validator_agent.name,
            message_type=MessageType.REQUEST,
            action="validate_roster",
            payload={
                "roster": roster_result.get("roster", []),
                "days": days,
                "store": store_data,
            },
        )
        validate_result = self.validator_agent.process(validate_msg)
        validation = validate_result.payload
        self._log_step("VALIDATE", f"Found {validation.get('total_conflicts', 0)} conflicts")
        
        # Step 5: Resolve conflicts with ResolverAgent (if any)
        resolved_roster = roster_result.get("roster", [])
        resolution_summary = None
        
        if validation.get("conflicts"):
            self._log_step("RESOLVE", "Resolving scheduling conflicts")
            resolve_msg = AgentMessage(
                sender=self.name,
                recipient=self.resolver_agent.name,
                message_type=MessageType.REQUEST,
                action="resolve_conflicts",
                payload={
                    "conflicts": validation.get("conflicts", []),
                    "roster": roster_result.get("roster", []),
                    "employees": employees_data,
                },
            )
            resolve_result = self.resolver_agent.process(resolve_msg)
            resolution_summary = resolve_result.payload
            resolved_roster = resolution_summary.get("modified_roster", roster_result.get("roster", []))
            self._log_step("RESOLVE", f"Applied {resolution_summary.get('resolutions_applied', 0)} resolutions")
        
        # Final validation
        self._log_step("FINAL", "Running final validation")
        final_validate_msg = AgentMessage(
            sender=self.name,
            recipient=self.validator_agent.name,
            message_type=MessageType.REQUEST,
            action="validate_roster",
            payload={
                "roster": resolved_roster,
                "days": days,
                "store": store_data,
            },
        )
        final_validation = self.validator_agent.process(final_validate_msg).payload
        
        total_time = time.time() - start_time
        self.set_status("complete")
        self._log_step("COMPLETE", f"Workflow completed in {total_time:.2f}s")
        
        return {
            "status": "success" if final_validation.get("is_valid") else "partial",
            "roster": resolved_roster,
            "days": days,
            "total_employees": len(employees_data),
            "generation_time_seconds": round(total_time, 2),
            "demand_analysis": demand_analysis,
            "skill_matching": skill_matching,
            "initial_validation": validation,
            "resolution_summary": resolution_summary,
            "final_validation": final_validation,
            "workflow_log": self.workflow_log,
            "peak_coverage": roster_result.get("peak_coverage", {}),
            "agents_used": [
                self.demand_agent.name,
                self.matcher_agent.name,
                self.validator_agent.name,
                self.resolver_agent.name,
            ],
        }
    
    def _log_step(self, stage: str, message: str) -> None:
        """Log a workflow step."""
        self.workflow_log.append({
            "timestamp": time.time(),
            "stage": stage,
            "message": message,
        })
    
    def _convert_to_store(self, store_data: Dict[str, Any]) -> Store:
        """Convert store dict to Store model."""
        normal_reqs = store_data.get("normal_requirements", {})
        peak_reqs = store_data.get("peak_requirements", normal_reqs)
        
        normal = StaffingRequirement(
            kitchen_staff=normal_reqs.get("kitchen_staff", 3),
            counter_staff=normal_reqs.get("counter_staff", 3),
            mccafe_staff=normal_reqs.get("mccafe_staff", 0),
            dessert_station_staff=normal_reqs.get("dessert_station_staff", 0),
            offline_dessert_station_staff=normal_reqs.get("offline_dessert_station_staff", 0),
        )
        
        peak = StaffingRequirement(
            kitchen_staff=peak_reqs.get("kitchen_staff", 4),
            counter_staff=peak_reqs.get("counter_staff", 4),
            mccafe_staff=peak_reqs.get("mccafe_staff", 0),
            dessert_station_staff=peak_reqs.get("dessert_station_staff", 0),
            offline_dessert_station_staff=peak_reqs.get("offline_dessert_station_staff", 0),
        )
        
        location_str = store_data.get("location_type", "Suburban")
        if "CBD" in str(location_str):
            store_type = StoreType.CBD_CORE
        elif "Highway" in str(location_str):
            store_type = StoreType.HIGHWAY
        else:
            store_type = StoreType.SUBURBAN
        
        return Store(
            store_id=store_data.get("store_id", "store_1"),
            location_type=store_type,
            normal_requirements=normal,
            peak_requirements=peak,
        )
    
    def _convert_to_employees(self, employees_data: List[Dict[str, Any]]) -> List[Employee]:
        """Convert employee dicts to Employee models."""
        employees = []
        
        for emp_data in employees_data:
            emp_type_str = emp_data.get("employee_type", "Casual")
            if "Full" in str(emp_type_str):
                emp_type = EmployeeType.FULL_TIME
            elif "Part" in str(emp_type_str):
                emp_type = EmployeeType.PART_TIME
            else:
                emp_type = EmployeeType.CASUAL
            
            station_str = emp_data.get("primary_station", "Counter")
            if "Kitchen" in str(station_str):
                primary_station = Station.KITCHEN
            elif "McCafe" in str(station_str):
                primary_station = Station.MCCAFE
            elif "Multi" in str(station_str) and "McCafe" in str(station_str):
                primary_station = Station.MULTI_STATION_MCCAFE
            elif "Multi" in str(station_str):
                primary_station = Station.MULTI_STATION
            elif "Dessert" in str(station_str):
                primary_station = Station.DESSERT
            else:
                primary_station = Station.COUNTER
            
            employees.append(Employee(
                id=emp_data.get("id", f"emp_{len(employees)}"),
                name=emp_data.get("name", f"Employee {len(employees)}"),
                employee_type=emp_type,
                primary_station=primary_station,
                is_manager=emp_data.get("is_manager", False),
                availability=emp_data.get("availability", {}),
            ))
        
        return employees
