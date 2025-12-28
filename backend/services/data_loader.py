import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from models.employee import Employee, EmployeeType, Station
from models.store import Store, StoreType, StaffingRequirement
from models.shift import ShiftType


class DataLoader:
    """Load employee, store, and availability data from Excel/CSV files."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # Try multiple locations: data/ folder, parent directory, or current directory
            possible_dirs = [
                Path(__file__).parent.parent / "data",  # backend/data/
                Path(__file__).parent.parent.parent,    # project root
                Path(__file__).parent.parent,            # backend/
            ]
            for dir_path in possible_dirs:
                if (dir_path / "employee_availability_2weeks.xlsx").exists():
                    self.data_dir = dir_path
                    break
            else:
                self.data_dir = Path(__file__).parent.parent.parent  # Default to project root
        else:
            self.data_dir = Path(data_dir)
    
    def load_staff_estimates(self) -> pd.DataFrame:
        """Load store structure and staff estimates."""
        csv_path = self.data_dir / "store_structure_staff_estimate.csv"
        if csv_path.exists():
            return pd.read_csv(csv_path)
        return pd.DataFrame()
    
    def load_employee_availability(self) -> pd.DataFrame:
        """Load employee availability for 2 weeks."""
        xlsx_path = self.data_dir / "employee_availability_2weeks.xlsx"
        if xlsx_path.exists():
            # Header is at row 4 (0-indexed), skip metadata rows
            df = pd.read_excel(xlsx_path, header=4)
            # Rename date columns to ISO format
            col_mapping = {
                'ID': 'ID',
                'Employee Name': 'Employee Name',
                'Type': 'Type',
                'Station': 'Station',
            }
            # Map date columns from "Mon\nDec 9" format to "2024-12-09"
            date_mapping = {
                'Mon\nDec 9': '2024-12-09',
                'Tue\nDec 10': '2024-12-10',
                'Wed\nDec 11': '2024-12-11',
                'Thu\nDec 12': '2024-12-12',
                'Fri\nDec 13': '2024-12-13',
                'Sat\nDec 14': '2024-12-14',
                'Sun\nDec 15': '2024-12-15',
                'Mon\nDec 16': '2024-12-16',
                'Tue\nDec 17': '2024-12-17',
                'Wed\nDec 18': '2024-12-18',
                'Thu\nDec 19': '2024-12-19',
                'Fri\nDec 20': '2024-12-20',
                'Sat\nDec 21': '2024-12-21',
                'Sun\nDec 22': '2024-12-22',
            }
            col_mapping.update(date_mapping)
            df = df.rename(columns=col_mapping)
            df = df.dropna(subset=['ID'])
            return df
        return pd.DataFrame()
    
    def load_management_roster(self) -> pd.DataFrame:
        """Load management roster template."""
        xlsx_path = self.data_dir / "management_roster_simplified.xlsx"
        if xlsx_path.exists():
            df = pd.read_excel(xlsx_path, header=3)
            return df.dropna(how='all')
        return pd.DataFrame()
    
    def parse_stores(self) -> List[Store]:
        """Parse store configurations from CSV data."""
        df = self.load_staff_estimates()
        if df.empty:
            return self._get_default_stores()
        
        stores = []
        grouped = df.groupby('store_location_type')
        
        for location_type, group in grouped:
            normal_row = group[group['period_type'] == 'Normal'].iloc[0] if len(group[group['period_type'] == 'Normal']) > 0 else None
            peak_row = group[group['period_type'] == 'Peak'].iloc[0] if len(group[group['period_type'] == 'Peak']) > 0 else None
            
            if normal_row is None:
                continue
            
            def safe_int(val, default=0):
                try:
                    if pd.isna(val):
                        return default
                    return int(val)
                except:
                    return default
                
            normal_req = StaffingRequirement(
                kitchen_staff=safe_int(normal_row.get('kitchen_staff', 0)),
                counter_staff=safe_int(normal_row.get('counter_staff', 0)),
                mccafe_staff=safe_int(normal_row.get('mccafe_staff', 0)),
                dessert_station_staff=safe_int(normal_row.get('dessert_station_staff', 0)),
                offline_dessert_station_staff=safe_int(normal_row.get('offline_dessert_station_staff', 0)),
            )
            
            peak_req = StaffingRequirement(
                kitchen_staff=safe_int(peak_row.get('kitchen_staff', 0)) if peak_row is not None else normal_req.kitchen_staff + 1,
                counter_staff=safe_int(peak_row.get('counter_staff', 0)) if peak_row is not None else normal_req.counter_staff + 1,
                mccafe_staff=safe_int(peak_row.get('mccafe_staff', 0)) if peak_row is not None else normal_req.mccafe_staff,
                dessert_station_staff=safe_int(peak_row.get('dessert_station_staff', 0)) if peak_row is not None else normal_req.dessert_station_staff,
                offline_dessert_station_staff=safe_int(peak_row.get('offline_dessert_station_staff', 0)) if peak_row is not None else normal_req.offline_dessert_station_staff,
            )
            
            store_type = StoreType.SUBURBAN
            if "CBD" in str(location_type):
                store_type = StoreType.CBD_CORE
            elif "Highway" in str(location_type):
                store_type = StoreType.HIGHWAY
            
            store = Store(
                store_id=str(normal_row.get('store_id', f"store_{location_type}")),
                location_type=store_type,
                normal_requirements=normal_req,
                peak_requirements=peak_req,
            )
            stores.append(store)
        
        if not stores:
            return self._get_default_stores()
        return stores
    
    def _get_default_stores(self) -> List[Store]:
        """Return default store configuration."""
        return [
            Store(
                store_id="default_suburban",
                location_type=StoreType.SUBURBAN,
                normal_requirements=StaffingRequirement(
                    kitchen_staff=4,
                    counter_staff=4,
                    mccafe_staff=2,
                ),
                peak_requirements=StaffingRequirement(
                    kitchen_staff=6,
                    counter_staff=6,
                    mccafe_staff=3,
                ),
            )
        ]
    
    def parse_employees(self) -> List[Employee]:
        """Parse employee data and availability from Excel."""
        df = self.load_employee_availability()
        if df.empty:
            return []
        
        employees = []
        
        date_cols = [col for col in df.columns if col.startswith('2024-')]
        
        # List of known legend/metadata row IDs to skip
        skip_ids = [
            'Legend', 'Shift Codes:', '1F = First Half (06:30-15:30)',
            '2F = Second Half (14:00-23:00)', '3F = Full Day (08:00-20:00)',
            '/ = Not Available', 'Weekly Coverage Summary', 'Employment Type',
            'Full-Time', 'Part-Time', 'Casual', 'nan', ''
        ]
        
        for _, row in df.iterrows():
            emp_id = str(row.get('ID', ''))
            if not emp_id or emp_id == 'nan' or emp_id in skip_ids:
                continue
            
            # Skip if ID doesn't look like a valid employee ID (should be numeric)
            if not emp_id.isdigit() and not emp_id.startswith('E'):
                continue
            
            emp_type_str = str(row.get('Type', 'Casual'))
            if 'Full' in emp_type_str:
                emp_type = EmployeeType.FULL_TIME
            elif 'Part' in emp_type_str:
                emp_type = EmployeeType.PART_TIME
            else:
                emp_type = EmployeeType.CASUAL
            
            station_str = str(row.get('Station', 'Counter'))
            # Check Multi-Station first (more specific match)
            if 'Multi-Station McCafe' in station_str or ('Multi' in station_str and 'McCafe' in station_str):
                primary_station = Station.MULTI_STATION_MCCAFE
            elif 'Multi' in station_str:
                primary_station = Station.MULTI_STATION
            elif 'Kitchen' in station_str:
                primary_station = Station.KITCHEN
            elif 'McCafe' in station_str:
                primary_station = Station.MCCAFE
            elif 'Dessert' in station_str:
                primary_station = Station.DESSERT
            else:
                primary_station = Station.COUNTER
            
            availability = {}
            for col in date_cols:
                shift_code = str(row.get(col, ''))
                if shift_code and shift_code != 'nan' and shift_code.strip() and shift_code.strip() != '/':
                    availability[col] = [shift_code.strip()]
            
            certified = []
            is_manager = False
            
            # Multi-Station Full-Time employees are likely managers/supervisors
            if primary_station in [Station.MULTI_STATION, Station.MULTI_STATION_MCCAFE]:
                certified = [Station.KITCHEN, Station.COUNTER]
                if primary_station == Station.MULTI_STATION_MCCAFE:
                    certified.append(Station.MCCAFE)
                # Full-time multi-station employees are managers
                if emp_type == EmployeeType.FULL_TIME:
                    is_manager = True
            
            employee = Employee(
                id=emp_id,
                name=str(row.get('Employee Name', f'Employee {emp_id}')),
                employee_type=emp_type,
                primary_station=primary_station,
                certified_stations=certified,
                is_manager=is_manager,
                availability=availability,
            )
            employees.append(employee)
        
        return employees
    
    def parse_managers(self) -> List[Employee]:
        """Parse manager data from management roster."""
        df = self.load_management_roster()
        if df.empty:
            return []
        
        managers = []
        
        date_cols = [col for col in df.columns if 'Dec' in str(col) or 'Mon' in str(col) or 'Tue' in str(col)]
        
        for _, row in df.iterrows():
            role = str(row.iloc[0]) if len(row) > 0 else ''
            name = str(row.iloc[1]) if len(row) > 1 else ''
            
            if not name or name == 'nan' or 'Manager' not in role:
                continue
            
            availability = {}
            for i, col in enumerate(date_cols):
                if i + 4 < len(row):
                    shift_code = str(row.iloc[i + 4])
                    if shift_code and shift_code != 'nan' and shift_code.strip() and shift_code.strip() != '/':
                        try:
                            day_num = int(''.join(filter(str.isdigit, str(col))))
                            day_key = f"2024-12-{str(day_num).zfill(2)}"
                            availability[day_key] = [shift_code.strip()]
                        except:
                            pass
            
            manager = Employee(
                id=f"mgr_{name.lower().replace(' ', '_').replace('.', '')}",
                name=name,
                employee_type=EmployeeType.FULL_TIME,
                primary_station=Station.MULTI_STATION,
                certified_stations=[Station.KITCHEN, Station.COUNTER, Station.MCCAFE],
                is_manager=True,
                availability=availability,
            )
            managers.append(manager)
        
        return managers
    
    def get_all_data(self) -> Dict[str, Any]:
        """Load and parse all data."""
        stores = self.parse_stores()
        employees = self.parse_employees()
        managers = self.parse_managers()
        
        all_employees = employees + managers
        
        return {
            "stores": stores,
            "employees": all_employees,
            "managers": managers,
            "crew": employees,
            "total_employees": len(all_employees),
        }
