#!/usr/bin/env python3
"""Simple web server to view SQLite database as HTML with CSV export."""

import sqlite3
import json
import io
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
from threading import Timer

DB_PATH = Path(__file__).parent / "local.db"


class DBViewHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves database viewer."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/":
            self.serve_html()
        elif self.path == "/api/data":
            self.serve_data()
        elif self.path.startswith("/api/csv/"):
            table_name = self.path[9:]  # Remove "/api/csv/"
            self.serve_csv(table_name)
        else:
            self.send_error(404)

    def serve_html(self):
        """Serve the HTML page."""
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
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 18px;
            color: #666;
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
            overflow-x: auto;
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
            white-space: nowrap;
        }
        .data-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
            word-break: break-word;
            white-space: normal;
            vertical-align: top;
        }
        .data-table tbody tr:hover {
            background: #f9f9f9;
        }
        .table-controls {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            align-items: center;
        }
        .btn-download {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 13px;
            cursor: pointer;
            font-weight: 500;
        }
        .btn-download:hover {
            background: #5568d3;
        }
        .row-count {
            font-size: 13px;
            color: #666;
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
        <div id="content" class="loading">Loading database...</div>
    </div>

    <script>
        async function loadData() {
            console.log('loadData called');
            try {
                console.log('Fetching /api/data...');
                const response = await fetch('/api/data');
                console.log('Response status:', response.status);
                const dbData = await response.json();
                console.log('Data received:', dbData.tables ? dbData.tables.length + ' tables' : 'error');
                renderTables(dbData);
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('content').innerHTML = '<div class="empty">Error loading database: ' + error.message + '</div>';
            }
        }

        function downloadCSV(tableName, columns, rows) {
            // Build CSV content
            var csv = columns.map(function(col) { return '"' + col.name + '"'; }).join(',') + '\\n';
            rows.forEach(function(row) {
                csv += row.map(function(cell) {
                    var val = String(cell || '');
                    // Escape quotes and wrap in quotes
                    return '"' + val.split('"').join('""') + '"';
                }).join(',') + '\\n';
            });

            // Create blob and download
            var blob = new Blob([csv], { type: 'text/csv' });
            var url = window.URL.createObjectURL(blob);
            var link = document.createElement('a');
            link.href = url;
            link.download = tableName + '.csv';
            document.body.appendChild(link);
            link.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(link);
        }

        function renderTables(dbData) {
            var container = document.getElementById('content');
            container.innerHTML = '<p style="color: #666; margin-bottom: 30px;">Database: ' + dbData.path + '</p>';

            dbData.tables.forEach(function(table) {
                var section = document.createElement('div');
                section.className = 'table-section';

                // Header
                var header = document.createElement('div');
                header.className = 'table-header';
                header.innerHTML = '<h2>' + table.name + '</h2><div class="table-stats">' + table.rowCount + ' rows</div>';
                section.appendChild(header);

                // Content
                var content = document.createElement('div');
                content.className = 'table-content';

                // Schema
                var schemaDiv = document.createElement('div');
                schemaDiv.className = 'schema';
                schemaDiv.innerHTML = '<h3>Schema</h3>';

                var columnsDiv = document.createElement('div');
                columnsDiv.className = 'columns';

                table.columns.forEach(function(col) {
                    var item = document.createElement('div');
                    item.className = 'column-item';
                    var flagsHtml = col.flags ? '<div class="column-flags">' + col.flags + '</div>' : '';
                    item.innerHTML = '<div class="column-name">' + col.name + '</div><div class="column-type">' + col.type + '</div>' + flagsHtml;
                    columnsDiv.appendChild(item);
                });

                schemaDiv.appendChild(columnsDiv);
                content.appendChild(schemaDiv);

                // Controls
                if (table.rowCount > 0) {
                    var controls = document.createElement('div');
                    controls.className = 'table-controls';
                    var downloadBtn = document.createElement('button');
                    downloadBtn.className = 'btn-download';
                    downloadBtn.textContent = 'Download as CSV';
                    downloadBtn.onclick = function() { downloadCSV(table.name, table.columns, table.rows); };
                    controls.appendChild(downloadBtn);
                    var rowInfo = document.createElement('span');
                    rowInfo.className = 'row-count';
                    rowInfo.textContent = 'Showing ' + table.rows.length + ' of ' + table.rowCount + ' rows';
                    controls.appendChild(rowInfo);
                    content.appendChild(controls);
                }

                // Data
                if (table.rowCount > 0) {
                    var table_elem = document.createElement('table');
                    table_elem.className = 'data-table';

                    // Header
                    var thead = document.createElement('thead');
                    var headerRow = document.createElement('tr');
                    table.columns.forEach(function(col) {
                        var th = document.createElement('th');
                        th.textContent = col.name;
                        headerRow.appendChild(th);
                    });
                    thead.appendChild(headerRow);
                    table_elem.appendChild(thead);

                    // Body
                    var tbody = document.createElement('tbody');
                    if (table.rows.length > 0) {
                        table.rows.forEach(function(row) {
                            var tr = document.createElement('tr');
                            row.forEach(function(cell) {
                                var td = document.createElement('td');
                                td.textContent = String(cell || '');
                                tr.appendChild(td);
                            });
                            tbody.appendChild(tr);
                        });
                    }
                    table_elem.appendChild(tbody);
                    content.appendChild(table_elem);
                } else {
                    var empty = document.createElement('div');
                    empty.className = 'empty';
                    empty.textContent = 'No rows in this table';
                    content.appendChild(empty);
                }

                section.appendChild(content);
                container.appendChild(section);
            });
        }

        // Load data when page loads
        console.log('Script loaded, calling loadData...');
        window.onload = function() {
            console.log('Window loaded');
            loadData();
        };
    </script>
</body>
</html>"""

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def serve_data(self):
        """Serve database data as JSON."""
        try:
            conn = sqlite3.connect(str(DB_PATH))
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

                # Get first 100 rows for display (large tables would be too much JSON)
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 100;")
                rows = cursor.fetchall()

                db_data["tables"].append({
                    "name": table_name,
                    "columns": columns,
                    "rowCount": row_count,
                    "rows": rows
                })

            conn.close()

            response = json.dumps(db_data).encode()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        except Exception as e:
            error_response = json.dumps({"error": str(e)}).encode()
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-Length", str(len(error_response)))
            self.end_headers()
            self.wfile.write(error_response)
            print(f"Error in serve_data: {e}")

    def serve_csv(self, table_name):
        """Serve table data as CSV file."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Verify table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
            if not cursor.fetchone():
                self.send_error(404)
                conn.close()
                return

            # Get schema
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [row[1] for row in cursor.fetchall()]

            # Get all data
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()

            conn.close()

            # Build CSV
            output = io.StringIO()
            # Write header
            output.write(','.join(f'"{col}"' for col in columns) + '\n')
            # Write rows
            for row in rows:
                output.write(','.join(f'"{str(cell or "").replace('"', '""')}"' for cell in row) + '\n')

            csv_data = output.getvalue().encode()

            self.send_response(200)
            self.send_header("Content-type", "text/csv")
            self.send_header("Content-Disposition", f'attachment; filename="{table_name}.csv"')
            self.end_headers()
            self.wfile.write(csv_data)
        except Exception as e:
            self.send_error(500)

    def log_message(self, format, *args):
        """Log HTTP requests."""
        print(f"  {args[0]} {args[1]} {args[2]}")


def open_browser():
    """Open browser after a short delay."""
    webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        exit(1)

    # Find a free port
    import socket
    port = 8000
    while port < 8010:
        try:
            server = HTTPServer(("localhost", port), DBViewHandler)
            break
        except OSError:
            port += 1
    else:
        print("Could not find a free port")
        exit(1)

    url = f"http://localhost:{port}"
    print(f"📊 Database viewer running at {url}")
    print("Press Ctrl+C to stop")

    # Open browser automatically with correct port
    def open_browser_with_url():
        webbrowser.open(url)

    timer = Timer(1.0, open_browser_with_url)
    timer.daemon = True
    timer.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
