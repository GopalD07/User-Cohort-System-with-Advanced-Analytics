import json
import pandas as pd
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any, Set, Optional
import os


class UserCohortSystem:
    def __init__(self, n_users: int = 5000, seed: Optional[int] = 42):
        """
        n_users: number of synthetic users to generate (default 5000)
        seed: optional seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
        self.cohorts: List[Dict[str, Any]] = []
        self.now = datetime.now()
        self.user_profiles = self.generate_user_profiles(n_users)
        self.user_events = self.generate_sample_data(n_users)
        self.initialize_sample_cohorts()

    def generate_user_profiles(self, n_users: int) -> pd.DataFrame:
        """Generate user profile data including phone numbers."""
        profiles = []

        # Indian phone number prefixes for realistic data
        phone_prefixes = ['91', '92', '93', '94', '95', '96', '97', '98', '99']

        for i in range(1, n_users + 1):
            # Generate realistic Indian phone numbers
            prefix = random.choice(phone_prefixes)
            phone_number = f"+91{prefix}{random.randint(10000000, 99999999)}"

            profile = {
                'user_id': f"user_{i}",
                'phone_number': phone_number,
                'email': f"user{i}@example.com",
                'signup_date': self.now - timedelta(days=random.randint(1, 365)),
                'city': random.choice(['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Ahmedabad']),
                'age_group': random.choice(['18-25', '26-35', '36-45', '46-55', '55+']),
                'gender': random.choice(['Male', 'Female', 'Other'])
            }
            profiles.append(profile)

        return pd.DataFrame(profiles)

    def generate_sample_data(self, n_users: int) -> pd.DataFrame:
        """Generate sample user event data for testing (vectorized-ish)."""
        events = []
        user_ids = [f"user_{i}" for i in range(1, n_users + 1)]
        actions = [
            "cart_added",
            "payment_successful",
            "checkout_clicked",
            "PDP_view",
            "buy_now_clicked",
            "user_login",
            "user_signup",
            "wishlist_added",
        ]
        categories = ["men_shoe", "women_clothing", "electronics", "beauty"]
        brands = ["Nike", "Adidas", "Puma", "Apple", "Samsung"]

        now = self.now
        for uid in user_ids:
            num_events = random.randint(5, 20)
            for _ in range(num_events):
                action = random.choice(actions)
                # price only for cart_added or payment_successful
                if action == "cart_added":
                    price = random.randint(500, 8000)
                elif action == "payment_successful":
                    price = random.randint(300, 6000)
                else:
                    price = None

                event = {
                    "user_id": uid,
                    "event": action,
                    # spread events over last 30 days
                    "timestamp": now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23), minutes=random.randint(0, 59)),
                    "price": price,
                    "category": random.choice(categories),
                    "sku_id": f"SKU{random.randint(1000, 9999)}",
                    "brand": random.choice(brands),
                }
                events.append(event)

        df = pd.DataFrame(events)
        # normalize price: keep numeric or NaN for consistency
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        print(f"Generated {len(df)} events for {n_users} users")
        return df

    def initialize_sample_cohorts(self):
        """Initialize sample cohorts as provided in your example, plus premium tiers."""
        sample_cohorts = [
            {
                "id": 1,
                "name": "High Value Abandoned Cart",
                "description": "Users who added expensive items but didn't complete purchase",
                "conditions": [
                    {
                        "include": True,
                        "action": "cart_added",
                        "operation": "sum",
                        "property": "price",
                        "condition": ">=",
                        "value": 3000,
                        "timeframe": 7,
                        "logic": "AND",
                    },
                    {
                        "include": False,
                        "action": "payment_successful",
                        "operation": "count",
                        "property": "events",
                        "condition": ">=",
                        "value": 1,
                        "timeframe": 7,
                        "logic": None,
                    },
                ],
                "created_date": self.now.strftime("%Y-%m-%d"),
                "created_by": "System",
                "active": True,
            },
            {
                "id": 2,
                "name": "Checkout Abandoners",
                "description": "Users who started checkout but didn't complete payment",
                "conditions": [
                    {
                        "include": True,
                        "action": "checkout_clicked",
                        "operation": "count",
                        "property": "events",
                        "condition": ">=",
                        "value": 1,
                        "timeframe": 7,
                        "logic": "AND",
                    },
                    {
                        "include": False,
                        "action": "payment_successful",
                        "operation": "count",
                        "property": "events",
                        "condition": ">=",
                        "value": 1,
                        "timeframe": 7,
                        "logic": None,
                    },
                ],
                "created_date": self.now.strftime("%Y-%m-%d"),
                "created_by": "System",
                "active": True,
            },
            {
                "id": 3,
                "name": "Browser Non-Purchasers",
                "description": "Users who browse extensively but don't add to cart",
                "conditions": [
                    {
                        "include": True,
                        "action": "PDP_view",
                        "operation": "count",
                        "property": "events",
                        "condition": ">=",
                        "value": 5,
                        "timeframe": 7,
                        "logic": "AND",
                    },
                    {
                        "include": False,
                        "action": "cart_added",
                        "operation": "count",
                        "property": "events",
                        "condition": ">=",
                        "value": 1,
                        "timeframe": 7,
                        "logic": None,
                    },
                ],
                "created_date": self.now.strftime("%Y-%m-%d"),
                "created_by": "System",
                "active": True,
            },
        ]

        # === PREMIUM TIERS: Platinum / Gold / Silver ===
        # These cohorts use attributes available in the dataset:
        # - total_purchase_value (sum of 'payment_successful' price within a timeframe)
        # - purchase_count (count of 'payment_successful' events within a timeframe)
        # - avg_cart_value (average 'cart_added' price within a timeframe)
        # - recency: modeled as "at least one payment_successful in the recent timeframe"
        # Thresholds chosen as reasonable defaults — tweak to match your real business numbers.

        premium_cohorts = [
            {
                "id": 4,
                "name": "Platinum",
                "description": "Top-tier premium customers: high LTV, frequent buyers, and recent purchasers",
                "conditions": [
                    # High lifetime (last 365 days) purchase value
                    {
                        "include": True,
                        "action": "payment_successful",
                        "operation": "sum",
                        "property": "price",
                        "condition": ">=",
                        "value": 15000,  # ₹15,000 in last 365 days
                        "timeframe": 365,
                        "logic": "AND",
                    },
                    # Frequent purchasers
                    {
                        "include": True,
                        "action": "payment_successful",
                        "operation": "count",
                        "property": "events",
                        "condition": ">=",
                        "value": 5,  # at least 5 purchases in last 365 days
                        "timeframe": 365,
                        "logic": "AND",
                    },
                    # High average cart value
                    {
                        "include": True,
                        "action": "cart_added",
                        "operation": "avg",
                        "property": "price",
                        "condition": ">=",
                        "value": 2000,  # avg cart >= ₹2,000
                        "timeframe": 365,
                        "logic": "AND",
                    },
                    # Recent purchase (recency <= 90 days)
                    {
                        "include": True,
                        "action": "payment_successful",
                        "operation": "count",
                        "property": "events",
                        "condition": ">=",
                        "value": 1,
                        "timeframe": 90,
                        "logic": None,
                    },
                ],
                "created_date": self.now.strftime("%Y-%m-%d"),
                "created_by": "System",
                "active": True,
            },
            {
                "id": 5,
                "name": "Gold",
                "description": "Mid-tier premium customers: good spenders and somewhat frequent buyers",
                "conditions": [
                    {
                        "include": True,
                        "action": "payment_successful",
                        "operation": "sum",
                        "property": "price",
                        "condition": ">=",
                        "value": 7000,  # ₹7,000 in last 365 days
                        "timeframe": 365,
                        "logic": "AND",
                    },
                    {
                        "include": True,
                        "action": "payment_successful",
                        "operation": "count",
                        "property": "events",
                        "condition": ">=",
                        "value": 3,  # at least 3 purchases in last 365 days
                        "timeframe": 365,
                        "logic": "AND",
                    },
                    {
                        "include": True,
                        "action": "cart_added",
                        "operation": "avg",
                        "property": "price",
                        "condition": ">=",
                        "value": 1000,  # avg cart >= ₹1,000
                        "timeframe": 365,
                        "logic": "AND",
                    },
                    {
                        "include": True,
                        "action": "payment_successful",
                        "operation": "count",
                        "property": "events",
                        "condition": ">=",
                        "value": 1,
                        "timeframe": 180,  # recent purchase in last 180 days
                        "logic": None,
                    },
                ],
                "created_date": self.now.strftime("%Y-%m-%d"),
                "created_by": "System",
                "active": True,
            },
            {
                "id": 6,
                "name": "Silver",
                "description": "Entry premium: some spend and at least one recent purchase",
                "conditions": [
                    {
                        "include": True,
                        "action": "payment_successful",
                        "operation": "sum",
                        "property": "price",
                        "condition": ">=",
                        "value": 2000,  # ₹2,000 in last 365 days
                        "timeframe": 365,
                        "logic": "AND",
                    },
                    {
                        "include": True,
                        "action": "payment_successful",
                        "operation": "count",
                        "property": "events",
                        "condition": ">=",
                        "value": 1,  # at least 1 purchase in last 365 days
                        "timeframe": 365,
                        "logic": "AND",
                    },
                    {
                        "include": True,
                        "action": "cart_added",
                        "operation": "avg",
                        "property": "price",
                        "condition": ">=",
                        "value": 500,  # avg cart >= ₹500
                        "timeframe": 365,
                        "logic": "AND",
                    },
                    {
                        "include": True,
                        "action": "payment_successful",
                        "operation": "count",
                        "property": "events",
                        "condition": ">=",
                        "value": 1,
                        "timeframe": 365,  # recent purchase in last year
                        "logic": None,
                    },
                ],
                "created_date": self.now.strftime("%Y-%m-%d"),
                "created_by": "System",
                "active": True,
            },
        ]

        # append without changing existing cohort definitions
        sample_cohorts.extend(premium_cohorts)
        self.cohorts = sample_cohorts

    def _users_meeting_condition(self, condition: Dict[str, Any]) -> Set[str]:
        """
        Return the set of users who meet the raw condition (without include/exclude flip).
        This computes the metric per user for that condition and then returns users satisfying the condition operator.
        """
        action = condition["action"]
        operation = condition["operation"]
        prop = condition.get("property", "")
        timeframe = int(condition.get("timeframe", 30))
        cutoff = self.now - timedelta(days=timeframe)

        # filter once per condition
        filtered = self.user_events[
            (self.user_events["event"] == action) & (self.user_events["timestamp"] >= cutoff)
        ]
        if filtered.empty:
            return set()

        if operation == "count":
            grp = filtered.groupby("user_id").size()
            # grp is Series user_id -> count
            if condition["condition"] == ">=":
                users = set(grp[grp >= condition["value"]].index)
            elif condition["condition"] == ">":
                users = set(grp[grp > condition["value"]].index)
            elif condition["condition"] == "<=":
                users = set(grp[grp <= condition["value"]].index)
            elif condition["condition"] == "<":
                users = set(grp[grp < condition["value"]].index)
            elif condition["condition"] == "==":
                users = set(grp[grp == condition["value"]].index)
            else:
                users = set()
            return users

        elif operation == "sum" and prop == "price":
            grp = filtered.groupby("user_id")["price"].sum().fillna(0)
            if condition["condition"] == ">=":
                users = set(grp[grp >= condition["value"]].index)
            elif condition["condition"] == ">":
                users = set(grp[grp > condition["value"]].index)
            elif condition["condition"] == "<=":
                users = set(grp[grp <= condition["value"]].index)
            elif condition["condition"] == "<":
                users = set(grp[grp < condition["value"]].index)
            elif condition["condition"] == "==":
                users = set(grp[grp == condition["value"]].index)
            else:
                users = set()
            return users

        elif operation == "avg" and prop == "price":
            grp = filtered.groupby("user_id")["price"].mean().fillna(0)
            if condition["condition"] == ">=":
                users = set(grp[grp >= condition["value"]].index)
            elif condition["condition"] == ">":
                users = set(grp[grp > condition["value"]].index)
            elif condition["condition"] == "<=":
                users = set(grp[grp <= condition["value"]].index)
            elif condition["condition"] == "<":
                users = set(grp[grp < condition["value"]].index)
            elif condition["condition"] == "==":
                users = set(grp[grp == condition["value"]].index)
            else:
                users = set()
            return users

        elif operation == "distinct_count":
            # property might be 'sku_id' or others
            target_prop = prop if prop else "sku_id"
            grp = filtered.groupby("user_id")[target_prop].nunique()
            if condition["condition"] == ">=":
                users = set(grp[grp >= condition["value"]].index)
            elif condition["condition"] == ">":
                users = set(grp[grp > condition["value"]].index)
            elif condition["condition"] == "<=":
                users = set(grp[grp <= condition["value"]].index)
            elif condition["condition"] == "<":
                users = set(grp[grp < condition["value"]].index)
            elif condition["condition"] == "==":
                users = set(grp[grp == condition["value"]].index)
            else:
                users = set()
            return users

        else:
            # fallback: treat as count
            grp = filtered.groupby("user_id").size()
            if condition["condition"] == ">=":
                return set(grp[grp >= condition["value"]].index)
            elif condition["condition"] == ">":
                return set(grp[grp > condition["value"]].index)
            elif condition["condition"] == "<=":
                return set(grp[grp <= condition["value"]].index)
            elif condition["condition"] == "<":
                return set(grp[grp < condition["value"]].index)
            elif condition["condition"] == "==":
                return set(grp[grp == condition["value"]].index)
            else:
                return set()

    def execute_cohort(self, cohort: Dict[str, Any], debug: bool = False) -> List[str]:
        """
        Execute cohort logic using set operations for speed & clarity.
        Supports 'logic' = 'AND' / 'OR' between conditions. If logic is None -> treated as 'AND'.
        """
        universe = set(self.user_events["user_id"].unique())

        if debug:
            print(f"\nDEBUG: Evaluating cohort '{cohort['name']}' (universe size={len(universe)})")

        conditions = cohort.get("conditions", [])
        if not conditions:
            return []

        current_set: Optional[Set[str]] = None

        for i, cond in enumerate(conditions):
            met_users = self._users_meeting_condition(cond)

            # apply include/exclude
            if cond.get("include", True):
                cond_users = met_users
            else:
                cond_users = universe - met_users

            if debug and i < 5:
                print(f"  Cond {i+1}: action={cond['action']} op={cond['operation']} include={cond['include']} met={len(met_users)} -> cond_users={len(cond_users)}")

            if current_set is None:
                current_set = cond_users
            else:
                logic = (cond.get("logic") or "AND").upper()
                if logic == "AND":
                    current_set &= cond_users
                elif logic == "OR":
                    current_set |= cond_users
                else:
                    # unknown logic -> default to AND
                    current_set &= cond_users

        if current_set is None:
            return []

        if debug:
            print(f"Final matching users: {len(current_set)}")

        # return sorted list for reproducibility
        return sorted(list(current_set))

    def create_cohort(self, name: str, description: str, conditions: List[Dict]) -> Dict:
        cohort = {
            "id": len(self.cohorts) + 1,
            "name": name,
            "description": description,
            "conditions": conditions,
            "created_date": self.now.strftime("%Y-%m-%d"),
            "created_by": "User",
            "active": True,
        }
        self.cohorts.append(cohort)
        return cohort

    def get_cohort_users(self, cohort_id: int) -> List[str]:
        cohort = next((c for c in self.cohorts if c["id"] == cohort_id), None)
        if not cohort or not cohort.get("active", False):
            return []
        return self.execute_cohort(cohort)

    def analyze_cohorts(self, debug: bool = False) -> pd.DataFrame:
        results = []
        for cohort in self.cohorts:
            if cohort.get("active", False):
                users = self.execute_cohort(cohort, debug=debug)
                results.append(
                    {
                        "cohort_id": cohort["id"],
                        "cohort_name": cohort["name"],
                        "description": cohort.get("description", ""),
                        "user_count": len(users),
                        "created_date": cohort.get("created_date", ""),
                        "conditions_count": len(cohort.get("conditions", [])),
                    }
                )
        return pd.DataFrame(results)

    def _safe_sheet_name(self, name: str) -> str:
        # Excel sheet names must be <= 31 characters and cannot contain some characters
        invalid_chars = ['\\', '/', '*', '?', ':', '[', ']']
        safe = "".join("_" if c in invalid_chars else c for c in name)
        return safe[:31]

    def export_cohort_users(self, cohort_id: Optional[int] = None, filename: Optional[str] = None) -> str:
        """
        Export cohort user details to Excel file.
        Behavior:
         - If cohort_id provided: filename will use that cohort's name but the file will contain one sheet per active cohort,
           so you get cohorts divided into separate sheets in the same file.
         - If cohort_id is None: filename will default to 'all_cohorts_export.xlsx' and export all active cohorts similarly.
        """
        # choose filename based on provided cohort (if any)
        cohort_for_name = next((c for c in self.cohorts if c["id"] == cohort_id), None) if cohort_id is not None else None
        if not filename:
            if cohort_for_name:
                safe_name = cohort_for_name["name"].replace(" ", "_").replace("/", "_")[:20]
                filename = f"cohorts_export_{cohort_for_name['id']}_{safe_name}.xlsx"
            else:
                filename = "cohorts_export_all.xlsx"

        # Collect data per cohort
        cohort_sheets: Dict[str, pd.DataFrame] = {}
        summary_rows = []

        for cohort in self.cohorts:
            if not cohort.get("active", False):
                continue

            users = self.get_cohort_users(cohort["id"])

            user_data = []
            for user_id in users:
                # Get user profile information
                profile_df = self.user_profiles[self.user_profiles["user_id"] == user_id]
                user_profile = profile_df.iloc[0] if not profile_df.empty else None

                user_events = self.user_events[self.user_events["user_id"] == user_id]
                recent_events = user_events[user_events["timestamp"] >= self.now - timedelta(days=30)]

                last_activity = None
                if not user_events.empty:
                    last_activity = user_events["timestamp"].max().strftime("%Y-%m-%d %H:%M:%S")

                total_purchase_value = float(user_events[user_events["event"] == "payment_successful"]["price"].sum(skipna=True))
                unique_categories = user_events["category"].nunique()
                unique_brands = user_events["brand"].nunique()
                unique_skus = user_events["sku_id"].nunique()

                user_info = {
                    "user_id": user_id,
                    "phone_number": user_profile["phone_number"] if user_profile is not None else "N/A",
                    "email": user_profile["email"] if user_profile is not None else f"{user_id}@example.com",
                    "city": user_profile["city"] if user_profile is not None else "Unknown",
                    "age_group": user_profile["age_group"] if user_profile is not None else "Unknown",
                    "gender": user_profile["gender"] if user_profile is not None else "Unknown",
                    "signup_date": user_profile["signup_date"].strftime("%Y-%m-%d") if user_profile is not None else "Unknown",
                    "total_events": int(len(user_events)),
                    "recent_events": int(len(recent_events)),
                    "last_activity": last_activity,
                    "total_cart_value": float(user_events[user_events["event"] == "cart_added"]["price"].sum(skipna=True)),
                    "total_purchase_value": total_purchase_value,
                    "cart_additions": int(len(user_events[user_events["event"] == "cart_added"])),
                    "purchases": int(len(user_events[user_events["event"] == "payment_successful"])),
                    "page_views": int(len(user_events[user_events["event"] == "PDP_view"])),
                    "checkouts": int(len(user_events[user_events["event"] == "checkout_clicked"])),
                    "logins": int(len(user_events[user_events["event"] == "user_login"])),
                    "wishlist_additions": int(len(user_events[user_events["event"] == "wishlist_added"])),
                    "unique_categories_viewed": unique_categories,
                    "unique_brands_interacted": unique_brands,
                    "unique_products_viewed": unique_skus,
                    "conversion_rate": round((total_purchase_value / max(1, float(user_events[user_events["event"] == "cart_added"]["price"].sum(skipna=True)))) * 100, 2)
                                   if user_events[user_events["event"] == "cart_added"]["price"].sum(skipna=True) > 0 else 0
                }
                user_data.append(user_info)

            # Build DataFrame for this cohort
            if user_data:
                df_users = pd.DataFrame(user_data)
            else:
                # empty structure with expected columns
                columns = ["user_id", "phone_number", "email", "city", "age_group", "gender", "signup_date",
                           "total_events", "recent_events", "last_activity", "total_cart_value", "total_purchase_value",
                           "cart_additions", "purchases", "page_views", "checkouts", "logins", "wishlist_additions",
                           "unique_categories_viewed", "unique_brands_interacted", "unique_products_viewed", "conversion_rate"]
                df_users = pd.DataFrame(columns=columns)

            sheet_name = self._safe_sheet_name(f"Cohort_{cohort['id']}_{cohort['name']}")
            cohort_sheets[sheet_name] = df_users

            summary_rows.append({
                "Cohort ID": cohort["id"],
                "Cohort Name": cohort["name"],
                "Description": cohort.get("description", ""),
                "Total Users": len(users),
                "Created Date": cohort.get("created_date", ""),
                "Conditions Count": len(cohort.get("conditions", []))
            })

        # Create master summary dataframe
        cohort_summary_df = pd.DataFrame(summary_rows)

        # Also create aggregated summary stats (across cohorts)
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Write each cohort sheet
                for sheet, df_sheet in cohort_sheets.items():
                    # Excel forbids empty sheet names; ensure df_sheet is written even if empty
                    # If df_sheet is empty, write header-only
                    if df_sheet.empty:
                        # create a header-only DataFrame
                        header_df = pd.DataFrame(columns=df_sheet.columns)
                        header_df.to_excel(writer, sheet_name=sheet, index=False)
                    else:
                        df_sheet.to_excel(writer, sheet_name=sheet, index=False)

                # Cohorts summary sheet
                cohort_summary_df.to_excel(writer, sheet_name="Cohorts_Summary", index=False)

                # Optional: aggregated stats across all cohort users (union)
                # Build union of all cohort users and compute basic stats
                all_users_set = set()
                for df_sheet in cohort_sheets.values():
                    if "user_id" in df_sheet.columns and not df_sheet.empty:
                        all_users_set.update(df_sheet["user_id"].tolist())

                all_users_list = sorted(list(all_users_set))
                all_user_rows = []
                for user_id in all_users_list:
                    profile_df = self.user_profiles[self.user_profiles["user_id"] == user_id]
                    profile = profile_df.iloc[0] if not profile_df.empty else None
                    all_user_rows.append({
                        "user_id": user_id,
                        "phone_number": profile["phone_number"] if profile is not None else "N/A",
                        "email": profile["email"] if profile is not None else f"{user_id}@example.com",
                    })
                if all_user_rows:
                    pd.DataFrame(all_user_rows).to_excel(writer, sheet_name="All_Cohort_Users", index=False)
                else:
                    pd.DataFrame(columns=["user_id", "phone_number", "email"]).to_excel(writer, sheet_name="All_Cohort_Users", index=False)

            print(f"✓ Successfully exported cohort data to Excel file: {filename}")
            return filename

        except Exception as e:
            print(f"Error exporting to Excel: {e}")
            # Fallback to single CSV that contains summary of cohorts (because CSV cannot have multiple sheets)
            fallback_filename = filename.replace('.xlsx', '.csv')
            try:
                cohort_summary_df.to_csv(fallback_filename, index=False)
                print(f"✓ Fallback: Exported cohorts summary to CSV file: {fallback_filename}")
                return fallback_filename
            except Exception as e2:
                print(f"Fallback also failed: {e2}")
                raise

    def print_data_insights(self):
        print("\n" + "=" * 80)
        print("DATA INSIGHTS")
        print("=" * 80)
        print(f"Total Events: {len(self.user_events):,}")
        print(f"Unique Users: {self.user_events['user_id'].nunique():,}")
        print(f"User Profiles Generated: {len(self.user_profiles):,}")
        if not self.user_events.empty:
            print(
                f"Date Range: {self.user_events['timestamp'].min().strftime('%Y-%m-%d')} to {self.user_events['timestamp'].max().strftime('%Y-%m-%d')}"
            )

        print("\nEvent Distribution:")
        event_counts = self.user_events["event"].value_counts()
        for event, count in event_counts.items():
            print(f"  {event}: {count:,}")

        cart_events = self.user_events[self.user_events["event"] == "cart_added"]
        if len(cart_events) > 0:
            print(f"\nCart Statistics:")
            print(f"  Total Cart Events: {len(cart_events):,}")
            print(f"  Average Cart Value: ₹{cart_events['price'].mean():.2f}")
            print(f"  Max Cart Value: ₹{cart_events['price'].max():.2f}")
            print(f"  Min Cart Value: ₹{cart_events['price'].min():.2f}")

        high_value_carts = cart_events[cart_events["price"] >= 3000]
        print(f"  High Value Carts (≥₹3000): {len(high_value_carts):,}")
        print(f"  Users with High Value Carts: {high_value_carts['user_id'].nunique():,}")

        # User profile insights
        print(f"\nUser Profile Distribution:")
        print(f"  Cities: {', '.join(self.user_profiles['city'].value_counts().head().index.tolist())}")
        print(f"  Age Groups: {dict(self.user_profiles['age_group'].value_counts())}")
        print(f"  Gender Distribution: {dict(self.user_profiles['gender'].value_counts())}")

    def print_cohort_summary(self, debug: bool = False):
        print("=" * 80)
        print("USER COHORT ANALYSIS SUMMARY")
        print("=" * 80)
        summary = self.analyze_cohorts(debug=debug)
        if summary.empty:
            print("No active cohorts found.")
            return
        print(f"\nTotal Active Cohorts: {len(summary)}")
        print(f"Total Users Across All Cohorts: {summary['user_count'].sum():,}")
        print(f"Average Cohort Size: {summary['user_count'].mean():.0f}")

        print("\n" + "-" * 80)
        print("COHORT DETAILS:")
        print("-" * 80)
        for _, row in summary.iterrows():
            print(f"\nCohort #{row['cohort_id']}: {row['cohort_name']}")
            print(f"  Description: {row['description']}")
            print(f"  Users: {row['user_count']:,}")
            print(f"  Created: {row['created_date']}")
            print(f"  Conditions: {row['conditions_count']}")

        print("\n" + "=" * 80)


def main():
    print("Initializing User Cohort System...")
    system = UserCohortSystem(n_users=2000, seed=123)  # use fewer for quick demo

    # Show data insights first
    system.print_data_insights()

    print("\nGenerating cohort analysis...")
    system.print_cohort_summary(debug=True)

    # Create simple test cohorts
    simple_conditions = [
        {
            "include": True,
            "action": "cart_added",
            "operation": "count",
            "property": "events",
            "condition": ">=",
            "value": 1,
            "timeframe": 30,
            "logic": None,
        }
    ]
    system.create_cohort("Cart Users", "Users who added items to cart in last 30 days", simple_conditions)

    view_conditions = [
        {
            "include": True,
            "action": "PDP_view",
            "operation": "count",
            "property": "events",
            "condition": ">=",
            "value": 1,
            "timeframe": 30,
            "logic": None,
        }
    ]
    system.create_cohort("Product Viewers", "Users who viewed products in last 30 days", view_conditions)

    print("\nUpdated cohort analysis:")
    system.print_cohort_summary()

    # Export the largest cohort if exists (the export now creates one sheet per cohort inside the Excel file)
    summary = system.analyze_cohorts()
    if not summary.empty:
        largest_cohort_id = int(summary.loc[summary["user_count"].idxmax(), "cohort_id"])
        print("\n" + "=" * 80)
        print("EXPORTING COHORTS TO EXCEL (one sheet per cohort)...")
        print("=" * 80)
        filename = system.export_cohort_users(largest_cohort_id)
        print(f"Exported cohort users to: {filename}")

        if os.path.exists(filename):
            # Show a preview of sheets inside the file (if possible)
            try:
                excel_file = pd.ExcelFile(filename)
                print(f"\nExcel file contains {len(excel_file.sheet_names)} sheets:")
                for sheet in excel_file.sheet_names:
                    print(f"  - {sheet}")
                # show first few rows of the largest cohort sheet if present
                target_cohort = next((c for c in system.cohorts if c["id"] == largest_cohort_id), None)
                if target_cohort:
                    target_sheet = system._safe_sheet_name(f"Cohort_{target_cohort['id']}_{target_cohort['name']}")
                    if target_sheet in excel_file.sheet_names:
                        sample_data = pd.read_excel(filename, sheet_name=target_sheet)
                        print(f"\nSample exported Excel data for '{target_cohort['name']}' ({len(sample_data)} users):")
                        print(sample_data.head())
            except Exception as e:
                print(f"Could not preview Excel file: {e}")


if __name__ == "__main__":
    main()
