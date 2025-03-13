import re
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from config import SQL_QUERIES, SKIP_TABLES, DEBUG_MODE, DB_CONFIG

class Database:
    def __init__(self, config):
        self.connection_string = URL.create(
            drivername="postgresql",
            username=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            host=DB_CONFIG['server'],
            database=DB_CONFIG['database']
        )

        self.db = create_engine(self.connection_string)

        self.tables_list = []
        self.views_list = []
        self.database_list = []

        self.tables_schema = {}
        self.views_schema = {}
        self.database_schema = {}

        self._initialize_tables()

    def _initialize_tables(self):
        """Initialize tables list and schema"""
        if (DEBUG_MODE):
            print(f"connecting to", DB_CONFIG["server"])
        with self.db.connect() as connection:
            if (DEBUG_MODE):
                print(f"Done.")
                print(f"Geting database Schema")

            # Get table names
            result = connection.execute(text(SQL_QUERIES["select_tables"]))
            rows = result.fetchall()
            n = 0
            for row in rows:
                if self._is_table_available(row[0]):
                    self.tables_list.append(row[0])
                    if (DEBUG_MODE):
                        n = n + 1
                        print(f"{n:>3} {row[0]}")
            if (DEBUG_MODE):
                print("")

            # Get views names
            result = connection.execute(text(SQL_QUERIES["select_views"]))
            rows = result.fetchall()
            n = 0
            for row in rows:
                if self._is_table_available(row[0]):
                    self.views_list.append(row[0])
                    if (DEBUG_MODE):
                        n = n + 1
                        print(f"{n:>3} {row[0]}")
            if (DEBUG_MODE):
                print("")

            # Get table schemas
            result = connection.execute(text(SQL_QUERIES["create_tables_schema"]))
            rows = result.fetchall()
            n = 0
            for row in rows:
                create_statement = row[0]
                # Extract table name from CREATE TABLE statement
                match = re.search(r'CREATE TABLE (\w+)', create_statement)
                if match:
                    table_name = match.group(1)
                    if self._is_table_available(table_name):
                        # Extract columns part from the CREATE TABLE statement
                        columns_match = re.search(r'\((.*?)\)', create_statement)
                        if columns_match:
                            self.database_schema[table_name] = create_statement
                            if (DEBUG_MODE):
                                n = n + 1
                                print(f"{n:>3} {create_statement}")
            # result = connection.execute(text(SQL_QUERIES["create_tables_schema"]))
            # rows = result.fetchall()
            # n = 0
            # for row in rows:
            #     if self._is_table_available(row[0]):
            #         self.tables_schema.append(row[0])
            #         if (DEBUG_MODE):
            #             n = n + 1
            #             print(f"{n:>3} {row[0]}")
            if (DEBUG_MODE):
                print("")

            # Get views schemas
            result = connection.execute(text(SQL_QUERIES["create_views_schema"]))
            rows = result.fetchall()
            n = 0
            for row in rows:
                create_statement = row[0]
                # Extract table name from CREATE TABLE statement
                match = re.search(r'CREATE VIEW (\w+)', create_statement)
                if match:
                    table_name = match.group(1)
                    if self._is_table_available(table_name):
                        # Extract columns part from the CREATE TABLE statement
                        columns_match = re.search(r'\((.*?)\)', create_statement)
                        if columns_match:
                            self.database_schema[table_name] = create_statement
                            if (DEBUG_MODE):
                                n = n + 1
                                print(f"{n:>3} {create_statement}")


        # Join lists with newlines for prompt usage
        self.database_list = (
            "TABLES:\n```sql\n" + "\n".join(self.tables_list) + 
            "\n```\nVIEWS:\n```sql\n" + "\n".join(self.views_list) + "\n```"
        )
        # self.database_schema = "\n".join(self.tables_schema).join(self.views_schema)

        # self.tables_list = "\n".join(self.tables_list)
        # self.tables_schema = "\n".join(self.tables_schema)
        
        if (DEBUG_MODE):
            print("")
            print(f"Database Schema created.")

    def _is_table_available(self, table_name):
        """Check if table should be included"""
        return table_name not in SKIP_TABLES

    async def execute_query(self, query, fetch_size=100):
        try:
            with self.db.connect() as connection:
                result = connection.execute(text(query))

                header = [col[0] for col in result.cursor.description]

                rows = result.fetchmany(fetch_size)
                # If no rows returned, return empty list but with headers
                if not rows:
                    return [], header
            
                header = [col[0] for col in result.cursor.description]
                return rows, header
        
        except Exception as e:
            print(f"Error: {str(e)}")
            raise


    def get_tables_list(self):
        """Return formatted table list"""
        return self.tables_list
    
    def get_views_list(self):
        """Return formatted views list"""
        return self.views_list
    
    def get_database_list(self):
        """Return formatted tables and views list"""
        return self.database_list
    
    def get_database_schema(self):
        """Return formatted tables and views list"""
        return self.database_schema

    # def get_tables_schema(self):
    #     """Return formatted table schema"""
    #     return self.tables_schema
    
    # def get_views_schema(self):
    #     """Return formatted views schema"""
    #     return self.views_schema
    



