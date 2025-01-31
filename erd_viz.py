import streamlit as st
import pandas as pd
import graphviz

# Load the schema data
@st.cache_data
def load_data():
    return pd.read_csv('erd_2.csv')

# Load the data
df = load_data()

# Verify column names in the DataFrame
if not all(col in df.columns for col in ['Table', 'Column', 'Data Type']):
    st.error("The CSV file must contain 'Table', 'Column', and 'Data Type' columns.")
    st.stop()

# Filter only columns with Data Type = uniqueidentifier
df_uniqueidentifier = df[df['Data Type'] == 'uniqueidentifier']

# Cross-reference `uniqueidentifier` columns across tables to infer relationships
connections = []
for _, row in df_uniqueidentifier.iterrows():
    # Find matching `uniqueidentifier` columns in other tables
    matches = df_uniqueidentifier[(df_uniqueidentifier['Column'] == row['Column']) & (df_uniqueidentifier['Table'] != row['Table'])]
    for _, match in matches.iterrows():
        connections.append({
            'from_table': row['Table'],
            'from_column': row['Column'],
            'to_table': match['Table'],
            'to_column': match['Column']
        })

# Remove duplicate connections
connections_df = pd.DataFrame(connections).drop_duplicates()

# Streamlit UI
st.title("Entity Relationship Diagram Explorer")

# Filter Options: Table or Column Name
st.sidebar.header("Filter Options")
filter_type = st.sidebar.radio("Filter By", ("None", "Table Name", "Column Name"))

if filter_type == "Table Name":
    selected_table = st.sidebar.selectbox(
        "Select a Table (Type to Search)",
        df['Table'].unique(),
        help="Filter relationships by table name."
    )
    filtered_connections = connections_df[(connections_df['from_table'] == selected_table) | (connections_df['to_table'] == selected_table)]
elif filter_type == "Column Name":
    selected_column = st.sidebar.selectbox(
        "Select a Column (Type to Search)",
        df_uniqueidentifier['Column'].unique(),
        help="Filter relationships by column name."
    )
    # Identify tables containing the selected column
    tables_with_column = df_uniqueidentifier[df_uniqueidentifier['Column'] == selected_column]['Table'].unique()
    selected_table_1 = st.sidebar.selectbox(
        "Select First Table with the Column",
        tables_with_column,
        help="Select the first table containing the selected column."
    )
    # Filter connections for the first selected table
    filtered_connections_1 = connections_df[(connections_df['from_table'] == selected_table_1) | (connections_df['to_table'] == selected_table_1)]
    joinable_tables = filtered_connections_1['to_table'].unique()

    # Add selection for a second table
    selected_table_2 = st.sidebar.selectbox(
        "Select Second Table to Join",
        joinable_tables,
        help="Select a second table that can be joined using the selected column."
    )
    # Further filter connections for the second table
    filtered_connections = filtered_connections_1[
        (filtered_connections_1['to_table'] == selected_table_2) |
        (filtered_connections_1['from_table'] == selected_table_2)
    ]
else:
    filtered_connections = connections_df

# Add "Select To Table" dropdown for joinable tables
if filter_type == "Table Name" and 'selected_table' in locals():
    joinable_tables = filtered_connections['to_table'].unique()
    selected_to_table = st.sidebar.selectbox(
        "Select To Table (Joinable Tables)",
        joinable_tables,
        help="Select a table to explore joinable relationships."
    )
    filtered_connections = filtered_connections[filtered_connections['to_table'] == selected_to_table]

# Relationship Selection Dropdown
st.sidebar.header("Relationship Viewer")
selected_relationship = st.sidebar.selectbox(
    "Select a Relationship",
    filtered_connections.apply(lambda row: f"{row['from_table']} ({row['from_column']}) -> {row['to_table']} ({row['to_column']})", axis=1),
    help="View details for a specific relationship."
)

# Filter the selected relationship
selected_row = filtered_connections.loc[
    filtered_connections.apply(
        lambda row: f"{row['from_table']} ({row['from_column']}) -> {row['to_table']} ({row['to_column']})",
        axis=1
    ) == selected_relationship
].iloc[0]

from_table = selected_row['from_table']
from_column = selected_row['from_column']
to_table = selected_row['to_table']
to_column = selected_row['to_column']

# Visualize Joinable Tables Graph
st.subheader("Joinable Tables for Selected Table")
if 'selected_table' in locals():
    graph = graphviz.Digraph(format="png", engine="dot")
    graph.attr(rankdir="LR")  # Set orientation to horizontal

    # Add nodes for the selected table and its joinable tables
    graph.node(selected_table, selected_table, shape="box")
    for table in joinable_tables:
        graph.node(table, table, shape="box")
        graph.edge(selected_table, table, label="joins")

    st.graphviz_chart(graph)

# Display filtered tables side by side
st.subheader(f"Relationship: {from_table} ({from_column}) → {to_table} ({to_column})")
col1, col2 = st.columns(2)

with col1:
    st.write(f"**From Table: {from_table}**")
    st.dataframe(df[df['Table'] == from_table][['Column', 'Data Type']])

with col2:
    st.write(f"**To Table: {to_table}**")
    st.dataframe(df[df['Table'] == to_table][['Column', 'Data Type']])

# Graph Visualization for Selected Relationship
st.subheader("Visualize Relationship")
graph = graphviz.Digraph(format="png", engine="dot")
graph.attr(rankdir="LR")  # Set orientation to horizontal

# Add nodes and edge for the selected relationship
graph.node(from_table, from_table, shape="box")
graph.node(to_table, to_table, shape="box")
graph.edge(from_table, to_table, label=f"{from_column} → {to_column}")

# Add downstream joins for the "To Table"
downstream_connections = connections_df[connections_df['from_table'] == to_table]

if not downstream_connections.empty:
    for _, downstream_row in downstream_connections.iterrows():
        downstream_table = downstream_row['to_table']
        downstream_column = downstream_row['to_column']
        graph.node(downstream_table, downstream_table, shape="box")
        graph.edge(to_table, downstream_table, label=f"{to_column} → {downstream_column}")

# Display the graph
st.graphviz_chart(graph)
