import snowflake.connector

# Define your Snowflake connection details
connection_params = {
    'user': 'dhanusagg',
    'password': 'Sesi@123',
    'account': 'trb69882.us-east-1',
    'warehouse': 'COMPUTE_WH',
    'database': 'SNOWFLAKE',
    'schema': 'CORE',
    'role': 'ACCOUNTADMIN',  # Optional, depends on your setup
}

# Establish the connection
try:
    conn = snowflake.connector.connect(**connection_params)

    # Create a cursor object to interact with Snowflake
    cursor = conn.cursor()

    # Test the connection by executing a simple query (e.g., fetching the current version of Snowflake)
    cursor.execute("SELECT current_version()")

    # Fetch the result
    result = cursor.fetchone()
    print(f"Snowflake version: {result[0]}")

    # Close the cursor and connection
    cursor.close()
    conn.close()

    print("Connection successful!")

except snowflake.connector.errors.Error as e:
    print(f"Connection failed: {e}")
