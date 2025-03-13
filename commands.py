import re
import asyncio
from config import DEBUG_MODE
from table2ascii import table2ascii as t2a, PresetStyle
from langchain_core.prompts import PromptTemplate

class CommandHandler:
    def __init__(self, db, llm_chain, query_evaluator):
        self.db = db
        self.llm_chain = llm_chain
        self.query_eval = query_evaluator

    async def handle_hafsql(self, sql_query, user_display_name):
        """Handle !hafsql command - execute user query"""
        # sql_query = message.content.split(" ", 1)[1]
        try:
            rows, header = await self.db.execute_query(sql_query)
            # Check if the query returned empty results
            if not rows or not header:
                return "Query executed, but no results found. Please check your query."
            return await self._format_response(None, rows, header)
        except Exception as e:
            ai_explain = await self.handle_help(
                "Explain and/or suggest new query for this error format:\n" + str(e), user_display_name, False)
            return f"{ai_explain}\n\n```\n{str(e)}\n```"
        

    async def handle_aiquery(self, message, user_display_name):
        """Handle !aiquery command - try to create sql query from text"""
        # Use retry logic
        sql_query, rows, header = await self.retry_sql_generation(message, user_display_name)
        
        if sql_query:
            return await self._format_response(sql_query, rows, header)
        else:
            raise Exception("Failed to generate valid SQL query")


    async def handle_tablelist(self, message, user_display_name):
        """Handle !tablelist command - shows all available tables"""
        try:
            response = "Available Tables and Views:\n\n"
            response += self.db.get_database_list()
            response += "\n"
            return response
        except Exception as e:
            if (DEBUG_MODE):
                print(f"Error in !tablelist: {str(e)}")
            return (f"An error occurred: {str(e)}")


    async def handle_tableinfo(self, message, user_display_name):
        """Handle !tableinfo table_name - shows schema for specific table"""
        try:
            # Split message and get second word
            params = message.split()
            if len(params) < 2:
                return "Please specify a table name. Usage: !tableinfo <tablename>"
            
            table_name = params[1].lower()  # Get second word and convert to lowercase
            
            # Search for matching table schemas
            schema_dict = self.db.get_database_schema()
            matching_schemas = []
            for schema_table, create_stmt in schema_dict.items():
                if table_name in schema_table.lower():
                    matching_schemas.append(create_stmt)
            
            if matching_schemas:
                response = "Table Schema:\n```sql\n"
                response += "\n\n".join(matching_schemas)
                response += "\n```"
                return response
            else:
                return (f"No table schema found for '{table_name}'")
                
        except Exception as e:
            if (DEBUG_MODE):
                print(f"Error in !tableinfo: {str(e)}")
            return (f"An error occurred: {str(e)}")


    async def handle_help(self, help_text, user_display_name, include_tables=True):
        """Handle !help command - provides conversational help about tables and queries"""
        try:
            # Create help context with available information
            help_context = self._create_help_prompt()

            if (include_tables):
                tables_list = self.db.get_tables_list()
            else:
                tables_list = ""

            formatted_prompt = help_context.format(
                        help_text=help_text,
                        tables_list=tables_list,
                        username=user_display_name,
                        dialect="PostgreSQL"
                    )
            if (DEBUG_MODE):
                print("Formatted Prompt:", formatted_prompt)

            # Get response from LLM
            help_response = self.llm_chain.invoke(formatted_prompt)

            return help_response.content
                               
        except Exception as e:
            print(f"Error in !help: {str(e)}")
            return (f"An error occurred: {str(e)}")

    async def _format_response(self, sql_query, rows, header):
        """Format response data to readable table format"""
        output = t2a(
            header=header,
            body=rows,
            style=PresetStyle.thin_compact
        )
        
        with open("sqlresult.txt", "w", encoding='utf-8') as f:
            if sql_query:  # Only include query if it exists
                f.write(f"Query: {sql_query}\n\nResults:\n{output}")
            else:
                f.write(str(output))
        return "sqlresult.txt"
    
    def extract_JsonContent(self, text):
        # Extract SQL query block from different models response
        match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try to extract from generic Markdown code blocks
        match = re.search(r'```\n(.*?)\n```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try to extract the first code block, ignoring any text after it
        match = re.search(r'```(.*?)```', text, re.DOTALL)
        if match:
            # Extract content between first ``` and next ```
            inner_text = match.group(1)
            # Remove any language identifier if present
            inner_text = re.sub(r'^[a-zA-Z]+\n', '', inner_text)
            return inner_text.strip()

        # If no Markdown blocks found, clean and return the text
        return text.strip()

    def extract_sql(self, text):
        # Try to extract SQL inside Markdown code blocks with language
        match = re.search(r'```sql\n(.*?)\n```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try to extract from generic Markdown code blocks
        match = re.search(r'```\n(.*?)\n```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try to extract the first code block, ignoring any text after it
        match = re.search(r'```(.*?)```', text, re.DOTALL)
        if match:
            # Extract content between first ``` and next ```
            inner_text = match.group(1)
            # Remove any language identifier if present
            inner_text = re.sub(r'^[a-zA-Z]+\n', '', inner_text)
            return inner_text.strip()

        # If no Markdown blocks found, clean and return the text
        text = re.sub(r'\\(.)', r'\1', text)  # Remove escape characters
        return text.strip()
    

    async def retry_sql_generation(self, query_text, username, max_retries=3, retry_delay=2):
        """Attempt to execute AI Query with retries"""
        last_error = None

        for attempt in range(max_retries):
            try:
                # Get suggested tables
                suggested_tables = await self._get_suggested_tables(query_text)
                
                # Get and validate schemas
                relevant_schemas = await self._get_relevant_schemas(suggested_tables)
                
                # Generate and execute SQL query
                sql_query = await self._generate_sql_query(query_text, relevant_schemas, username)
                rows, header = await self.db.execute_query(sql_query)
                
                return sql_query, rows, header

            except Exception as e:
                last_error = str(e)
                query_text = await self._handle_retry_error(query_text, last_error, attempt, max_retries)
                await asyncio.sleep(retry_delay)

        return None, None, None

    async def _get_suggested_tables(self, query_text):
        """Get relevant tables based on user input"""
        evaluator_prompt = self._create_evaluator_prompt(query_text)
        formatted_prompt = evaluator_prompt.format(
            input=query_text,
            tables_list=self.db.get_database_list()
        )
        
        if DEBUG_MODE:
            print("Formatted Prompt:", formatted_prompt)

        llm_response = self.llm_chain.invoke(formatted_prompt)
        
        if DEBUG_MODE:
            print(f"Raw evaluator response: {llm_response.content}")

        return self._parse_table_suggestions(llm_response.content)

    def _parse_table_suggestions(self, content):
        """Parse table names from LLM response"""
        table_list_str = self.extract_JsonContent(content)
        table_list_str = table_list_str.replace('[', '').replace(']', '').strip()
        
        suggested_tables = [
            table.strip().strip('"\'[]') 
            for table in table_list_str.split(',')
            if table.strip()
        ]
        
        if DEBUG_MODE:
            print(f"Suggested tables: {suggested_tables}")
            
        return suggested_tables

    async def _get_relevant_schemas(self, suggested_tables):
        """Get schemas for suggested tables"""
        relevant_schemas = {}
        
        for table in suggested_tables:
            try:
                schema = self.db.get_database_schema().get(table)
                if schema:
                    relevant_schemas[table] = schema
                    if DEBUG_MODE:
                        print(f"Found schema for table: {table}")
            except KeyError as e:
                print(f"Warning: Table {table} not found in schema")
                continue

        if not relevant_schemas:
            raise Exception(f"No valid tables found among suggestions: {suggested_tables}")

        if DEBUG_MODE:
            print("-"*30)
            print(f"Relevant schemas: {relevant_schemas}")

        return relevant_schemas

    async def _generate_sql_query(self, query_text, relevant_schemas, username):
        """Generate SQL query using LLM"""
        schemas_info = "\n".join([
            f"{schema}"
            for table, schema in relevant_schemas.items()
        ])

        if DEBUG_MODE:
            print("-"*30)
            print(f"Schemas being used:\n{schemas_info}")

        try:
            sql_prompt = self._create_sql_prompt()
            formatted_prompt = sql_prompt.format(
                input=query_text,
                dialect="PostgreSQL",
                top_k=100,
                table_info=schemas_info,
                username=username
            )
            
            llm_response = self.llm_chain.invoke(formatted_prompt)
            sql_query = self.extract_sql(llm_response.content)
            
            print("--"*30)
            print(f"Generated SQL:\n{sql_query}")
            print("")
            
            return sql_query
            
        except Exception as e:
            print(f"Error generating SQL query: {e}")
            raise

    async def _handle_retry_error(self, query_text, error, attempt, max_retries):
        """Handle retry error and format error context"""
        error_context = f"""
Attempt failed with error: {error}
Please fix the SQL query considering the error message and tables schema.
Try Select more Tables or Views or columns.
"""
        print("=="*30)
        print(f"ERROR: ATTEMPT {attempt + 1} FAILED:\n{error}")
        print("")

        if attempt == max_retries - 1:
            raise Exception(f"Failed after {max_retries} attempts. Last error: {error}")

        return f"{query_text}\n\n{error_context}"
    

    def _create_sql_prompt(self):
        """
        Create a custom SQL query prompt template for SQL query generation.
        Args: top_k (int, optional): Default number of rows to limit in queries. Defaults to 5.
        Returns: PromptTemplate: A prompt template for SQL query generation
        """
        # Define the SQL prompt template
        SQL_PROMPT = """
You are an expert in {dialect}. Given an input question, generate a syntactically correct query.

# **Key SQL Guidelines:**
- **IMPORTANT: DO NOT create DELETE, UPDATE, or INSERT statements.**
- If the user asks for a specific number (e.g., "last post", "last 5 posts"), use that number after `LIMIT`.
- If no number is specified, default to `LIMIT {top_k}`.
- Use table and columns names as specified in the schema.
- Query only the necessary columns to answer the question. Avoid using "SELECT *"
- Avoid selecting just one column to provide more context in the result. 

# **Query Constraints:**
- **Ignore 'id' column** (used only for internal database purposes).
- The **username** in the `accounts_table` table is stored in the 'name' column.
- The **username** in the `comments` table is stored in the 'author' column.
- Posts and Comments are stored in the same 'comments' table. To find **posts**, always filter `title<>''`. For **comments**, always filter `title=''`. Contents are stored in the 'body' column.
- **Tracking transfers:** Use the `operation_transfer_table` table.

# **Tables Schema:**
{table_info}

{username} Question: {input}

RESPOND ONLY THE SQL Query:
"""

        return PromptTemplate(
            input_variables=['input', 'top_k', 'dialect', 'table_info', 'username'],
            template=SQL_PROMPT,
        )
    

    def _create_evaluator_prompt(self, input):
        """
        Create a custom SQL query prompt template for SQL query generation.
        Args: top_k (int, optional): Default number of rows to limit in queries. Defaults to 5.
        Returns: PromptTemplate: A prompt template for SQL query generation
        """
        TABLE_SELECTION_PROMPT = """
You are an expert mssql PostgreeSQL database analyst tasked with selecting the most relevant tables to answer a specific user query.

# Task Guidelines:
- Carefully analyze the user's question and the available tables
- For 'posts' use table 'comments'
- Select ONLY TABLES or VIEWS that are directly relevant to answering the query
- Consider table relationships, foreign keys, and potential joins
- Be comprehensive but precise in TABLES/VIEWS selection
- Avoid including unnecessary tables that won't contribute to the query

# Evaluation Criteria:
1. Direct data relevance
2. Potential for meaningful joins
3. Columns that match query requirements
4. Minimal but sufficient table set

# User Question: {input}

# Response Requirements:
- Respond ONLY with a JSON-formatted list of table names
- If no tables are relevant, return an empty list: []

# Important Notes:
- Be strategic and think through table relationships
- Consider implicit connections between tables
- Quality of table selection is crucial for query accuracy
- RAW Output No explanations

# OUTPUT JUST FORMAT:
```json
["Customers", "Orders", "Products"]
```

# Database Scheme:
{tables_list}
"""

        # Prompt Template
        return PromptTemplate(
            input_variables=['input', 'tables_list'],
            template=TABLE_SELECTION_PROMPT
        )
    
    def _create_help_prompt(self):
        HELP_PROMPT = """
You are a helpful {dialect} assistant. Help {username} understand how to query the Hive blockchain data.

{username} Question: {help_text}

Provide a helpful response with examples if applicable in Discord Markdown text.

# Queries Helper

# Available Commands:
- !aiquery: Generate SQL queries from natural language
- !hafsql: Execute direct SQL queries
- !tablelist: Show all available tables
- !tableinfo: Show specific table schema
- !help: Ask question so I can help

# Available Tables and Their Purpose:
{tables_list}

# Command Aliases
'aiquery': ['!aiquery', '!ai', '!ask'],
'hafsql': ['!hafsql', '!sql', '!query'],
'tablelist': ['!tablelist', '!tables', '!tl'],
'tableinfo': ['!tableinfo', '!info', '!ti'],
'help': ['!help', '!h', '!?']
"""
        return PromptTemplate(
            input_variables=['tables_list', 'help_text', 'dialect', 'username'],
            template=HELP_PROMPT
        )