#!/usr/bin/env python3
"""Generate HTML view of SQLite database."""

import sqlite3
from pathlib import Path
import json

DB_PATH = Path(__file__).parent / "local.db"
HTML_PATH = Path(__file__).parent / "view_db.html"


def get_db_data():
    """Get database schema and sample data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]

    db_data = {"path": str(DB_PATH), "tables": []}

    for table_name in tables:
        # Get schema
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = []
        for col_id, name, type_, notnull, dflt_value, pk in cursor.fetchall():
            flags = []
            if pk:
                flags.append("PK")
            if notnull:
                flags.append("NOT NULL")
            columns.append({
                "name": name,
                "type": type_,
                "flags": " ".join(flags)
            })

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        row_count = cursor.fetchone()[0]

        # Get sample data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 10;")
        rows = cursor.fetchall()

        db_data["tables"].append({
            "name": table_name,
            "columns": columns,
            "rowCount": row_count,
            "rows": rows
        })

    conn.close()
    return db_data


def generate_html(db_data):
    """Generate HTML from database data."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SQLite Database Viewer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: #222;
            margin-bottom: 30px;
            font-size: 28px;
        }
        .table-section {
            background: white;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .table-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .table-header h2 {
            font-size: 20px;
            margin: 0;
        }
        .table-stats {
            font-size: 14px;
            opacity: 0.9;
        }
        .table-content {
            padding: 20px;
        }
        .schema {
            margin-bottom: 20px;
        }
        .schema h3 {
            font-size: 14px;
            color: #555;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .columns {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }
        .column-item {
            background: #f9f9f9;
            padding: 10px 12px;
            border-radius: 4px;
            font-size: 13px;
            border-left: 3px solid #667eea;
        }
        .column-name {
            font-weight: 600;
            color: #333;
        }
        .column-type {
            color: #666;
            font-size: 12px;
        }
        .column-flags {
            color: #888;
            font-size: 11px;
        }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 13px;
        }
        .data-table thead {
            background: #f0f0f0;
            border-bottom: 2px solid #ddd;
        }
        .data-table th {
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
        }
        .data-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
            word-break: break-word;
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .data-table tbody tr:hover {
            background: #f9f9f9;
        }
        .data-table td:hover {
            white-space: normal;
            overflow: visible;
            background: #fff;
            z-index: 1;
        }
        .empty {
            color: #999;
            font-style: italic;
            padding: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 SQLite Database Viewer</h1>
        <p style="color: #666; margin-bottom: 30px;">Database: """ + db_data["path"] + """</p>
"""

    for table in db_data["tables"]:
        html += f"""
        <div class="table-section">
            <div class="table-header">
                <h2>📋 {table["name"]}</h2>
                <div class="table-stats">{table["rowCount"]} rows</div>
            </div>
            <div class="table-content">
                <div class="schema">
                    <h3>Schema</h3>
                    <div class="columns">
"""
        for col in table["columns"]:
            html += f"""                        <div class="column-item">
                            <div class="column-name">{col["name"]}</div>
                            <div class="column-type">{col["type"]}</div>
"""
            if col["flags"]:
                html += f"""                            <div class="column-flags">{col["flags"]}</div>
"""
            html += """                        </div>
"""

        html += """                    </div>
                </div>
"""

        if table["rowCount"] > 0:
            html += """                <table class="data-table">
                    <thead>
                        <tr>
"""
            for col in table["columns"]:
                html += f"""                            <th>{col["name"]}</th>
"""
            html += """                        </tr>
                    </thead>
                    <tbody>
"""
            for row in table["rows"]:
                html += """                        <tr>
"""
                for cell in row:
                    cell_str = str(cell or "")[:100]
                    html += f"""                            <td title="{cell_str}">{cell_str}</td>
"""
                html += """                        </tr>
"""
            if len(table["rows"]) < table["rowCount"]:
                html += f"""                        <tr><td colspan="{len(table["columns"])}" class="empty">... and {table["rowCount"] - len(table["rows"])} more rows</td></tr>
"""
            html += """                    </tbody>
                </table>
"""
        else:
            html += """                <div class="empty">📭 No rows in this table</div>
"""

        html += """            </div>
        </div>
"""

    html += """    </div>
</body>
</html>
"""
    return html


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        exit(1)

    print("Reading database...")
    db_data = get_db_data()

    print("Generating HTML...")
    html = generate_html(db_data)

    print(f"Writing to {HTML_PATH}...")
    with open(HTML_PATH, "w") as f:
        f.write(html)

    print(f"✅ Done! Open {HTML_PATH} in your browser")
