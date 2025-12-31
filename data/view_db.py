#!/usr/bin/env python3
"""Simple web server to view SQLite databases with sidebar navigation."""

import sqlite3
import json
import io
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser
from threading import Timer

DATA_DIR = Path(__file__).parent


class DBViewHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves database viewer."""

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/":
            self.serve_html()
        elif path == "/api/databases":
            self.serve_databases()
        elif path == "/api/tables":
            db = params.get("db", [None])[0]
            self.serve_tables(db)
        elif path == "/api/data":
            db = params.get("db", [None])[0]
            table = params.get("table", [None])[0]
            page = int(params.get("page", [1])[0])
            limit = int(params.get("limit", [50])[0])
            self.serve_data(db, table, page, limit)
        elif path == "/api/csv":
            db = params.get("db", [None])[0]
            table = params.get("table", [None])[0]
            self.serve_csv(db, table)
        else:
            self.send_error(404)

    def send_json(self, data, status=200):
        """Send JSON response."""
        response = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def serve_databases(self):
        """List all .db files in data directory."""
        try:
            dbs = sorted([f.name for f in DATA_DIR.glob("*.db")])
            self.send_json({"databases": dbs})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def serve_tables(self, db_name):
        """List tables in a database."""
        if not db_name:
            self.send_json({"error": "No database specified"}, 400)
            return
        try:
            db_path = DATA_DIR / db_name
            if not db_path.exists():
                self.send_json({"error": "Database not found"}, 404)
                return
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = []
            for (name,) in cursor.fetchall():
                cursor.execute(f"SELECT COUNT(*) FROM [{name}];")
                count = cursor.fetchone()[0]
                tables.append({"name": name, "rowCount": count})
            conn.close()
            self.send_json({"tables": tables})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def serve_data(self, db_name, table_name, page, limit):
        """Serve paginated table data."""
        if not db_name or not table_name:
            self.send_json({"error": "Database and table required"}, 400)
            return
        try:
            db_path = DATA_DIR / db_name
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get columns
            cursor.execute(f"PRAGMA table_info([{table_name}]);")
            columns = []
            for col_id, name, type_, notnull, dflt_value, pk in cursor.fetchall():
                flags = []
                if pk:
                    flags.append("PK")
                if notnull:
                    flags.append("NOT NULL")
                columns.append({"name": name, "type": type_, "flags": " ".join(flags)})

            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}];")
            total = cursor.fetchone()[0]

            # Get paginated rows
            offset = (page - 1) * limit
            cursor.execute(f"SELECT * FROM [{table_name}] LIMIT ? OFFSET ?;", (limit, offset))
            rows = cursor.fetchall()
            conn.close()

            self.send_json({
                "columns": columns,
                "rows": rows,
                "total": total,
                "page": page,
                "limit": limit,
                "totalPages": (total + limit - 1) // limit if total > 0 else 1
            })
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def serve_csv(self, db_name, table_name):
        """Serve full table as CSV."""
        if not db_name or not table_name:
            self.send_error(400)
            return
        try:
            db_path = DATA_DIR / db_name
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            cursor.execute(f"PRAGMA table_info([{table_name}]);")
            columns = [row[1] for row in cursor.fetchall()]

            cursor.execute(f"SELECT * FROM [{table_name}];")
            rows = cursor.fetchall()
            conn.close()

            output = io.StringIO()
            output.write(','.join(f'"{col}"' for col in columns) + '\n')
            for row in rows:
                output.write(','.join(f'"{str(cell or "").replace(chr(34), chr(34)+chr(34))}"' for cell in row) + '\n')

            csv_data = output.getvalue().encode()
            self.send_response(200)
            self.send_header("Content-type", "text/csv")
            self.send_header("Content-Disposition", f'attachment; filename="{table_name}.csv"')
            self.send_header("Content-Length", str(len(csv_data)))
            self.end_headers()
            self.wfile.write(csv_data)
        except Exception as e:
            self.send_error(500)

    def serve_html(self):
        """Serve the HTML page."""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database Viewer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #fafafa;
            color: #333;
            display: flex;
            height: 100vh;
        }
        .sidebar {
            width: 260px;
            background: #fff;
            border-right: 1px solid #e0e0e0;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }
        .sidebar-header {
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
            font-weight: 600;
            font-size: 15px;
            color: #444;
        }
        .sidebar-content {
            flex: 1;
            overflow-y: auto;
        }
        .db-item, .table-item {
            padding: 12px 20px;
            cursor: pointer;
            font-size: 14px;
            border-bottom: 1px solid #f0f0f0;
            transition: background 0.15s;
        }
        .db-item:hover, .table-item:hover { background: #f5f5f5; }
        .db-item.active { background: #e8f0fe; color: #1a73e8; font-weight: 500; }
        .table-item.active { background: #e8f0fe; color: #1a73e8; }
        .table-item { padding-left: 36px; }
        .table-count {
            float: right;
            font-size: 12px;
            color: #888;
            background: #f0f0f0;
            padding: 2px 8px;
            border-radius: 10px;
        }
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .main-header {
            padding: 20px 24px;
            background: #fff;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .main-header h1 {
            font-size: 18px;
            font-weight: 600;
            color: #333;
        }
        .main-header .info {
            font-size: 13px;
            color: #666;
        }
        .btn {
            background: #1a73e8;
            color: #fff;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 13px;
            cursor: pointer;
            font-weight: 500;
        }
        .btn:hover { background: #1557b0; }
        .btn:disabled { background: #ccc; cursor: not-allowed; }
        .table-container {
            flex: 1;
            overflow: auto;
            padding: 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        thead {
            position: sticky;
            top: 0;
            background: #f8f9fa;
            z-index: 1;
        }
        th {
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            color: #444;
            border-bottom: 2px solid #e0e0e0;
            white-space: nowrap;
        }
        td {
            padding: 10px 16px;
            border-bottom: 1px solid #eee;
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        td:hover { white-space: normal; word-break: break-word; }
        tr:hover { background: #f8f9fa; }
        .pagination {
            padding: 16px 24px;
            background: #fff;
            border-top: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .pagination-btns { display: flex; gap: 8px; }
        .pagination-info { font-size: 13px; color: #666; }
        .empty {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #888;
            font-size: 15px;
        }
        .loading { color: #666; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">Databases</div>
        <div class="sidebar-content" id="sidebar"></div>
    </div>
    <div class="main">
        <div class="main-header">
            <div>
                <h1 id="title">Select a table</h1>
                <div class="info" id="info"></div>
            </div>
            <button class="btn" id="downloadBtn" style="display:none">Download CSV</button>
        </div>
        <div class="table-container" id="content">
            <div class="empty">Select a database and table from the sidebar</div>
        </div>
        <div class="pagination" id="pagination" style="display:none">
            <div class="pagination-info" id="pageInfo"></div>
            <div class="pagination-btns">
                <button class="btn" id="prevBtn">Previous</button>
                <button class="btn" id="nextBtn">Next</button>
            </div>
        </div>
    </div>

    <script>
        var state = { db: null, table: null, page: 1, limit: 50, total: 0, totalPages: 1 };

        async function loadDatabases() {
            var res = await fetch('/api/databases');
            var data = await res.json();
            var sidebar = document.getElementById('sidebar');
            sidebar.innerHTML = '';
            data.databases.forEach(function(db) {
                var div = document.createElement('div');
                div.className = 'db-item';
                div.textContent = db;
                div.onclick = function() { selectDatabase(db); };
                sidebar.appendChild(div);
            });
        }

        async function selectDatabase(db) {
            state.db = db;
            state.table = null;
            document.querySelectorAll('.db-item').forEach(function(el) {
                el.className = 'db-item' + (el.textContent === db ? ' active' : '');
            });
            var res = await fetch('/api/tables?db=' + encodeURIComponent(db));
            var data = await res.json();
            var sidebar = document.getElementById('sidebar');
            var dbItems = sidebar.querySelectorAll('.db-item');
            sidebar.innerHTML = '';
            dbItems.forEach(function(el) { sidebar.appendChild(el); });

            var activeDb = sidebar.querySelector('.db-item.active');
            if (activeDb) {
                data.tables.forEach(function(t) {
                    var div = document.createElement('div');
                    div.className = 'table-item';
                    div.innerHTML = t.name + '<span class="table-count">' + t.rowCount + '</span>';
                    div.onclick = function() { selectTable(t.name); };
                    activeDb.insertAdjacentElement('afterend', div);
                });
            }
            document.getElementById('title').textContent = db;
            document.getElementById('info').textContent = data.tables.length + ' tables';
            document.getElementById('content').innerHTML = '<div class="empty">Select a table</div>';
            document.getElementById('pagination').style.display = 'none';
            document.getElementById('downloadBtn').style.display = 'none';
        }

        async function selectTable(table) {
            state.table = table;
            state.page = 1;
            document.querySelectorAll('.table-item').forEach(function(el) {
                el.className = 'table-item' + (el.textContent.split(/\\d/)[0].trim() === table ? ' active' : '');
            });
            await loadData();
        }

        async function loadData() {
            var url = '/api/data?db=' + encodeURIComponent(state.db) + '&table=' + encodeURIComponent(state.table) + '&page=' + state.page + '&limit=' + state.limit;
            var res = await fetch(url);
            var data = await res.json();

            state.total = data.total;
            state.totalPages = data.totalPages;

            document.getElementById('title').textContent = state.table;
            document.getElementById('info').textContent = data.total + ' rows';
            document.getElementById('downloadBtn').style.display = 'inline-block';
            document.getElementById('downloadBtn').onclick = function() {
                window.location.href = '/api/csv?db=' + encodeURIComponent(state.db) + '&table=' + encodeURIComponent(state.table);
            };

            var content = document.getElementById('content');
            if (data.rows.length === 0) {
                content.innerHTML = '<div class="empty">No data</div>';
                document.getElementById('pagination').style.display = 'none';
                return;
            }

            var html = '<table><thead><tr>';
            data.columns.forEach(function(col) {
                html += '<th>' + col.name + '</th>';
            });
            html += '</tr></thead><tbody>';
            data.rows.forEach(function(row) {
                html += '<tr>';
                row.forEach(function(cell) {
                    var val = cell === null ? '' : String(cell);
                    html += '<td title="' + val.replace(/"/g, '&quot;') + '">' + val + '</td>';
                });
                html += '</tr>';
            });
            html += '</tbody></table>';
            content.innerHTML = html;

            var pagination = document.getElementById('pagination');
            pagination.style.display = 'flex';
            var start = (state.page - 1) * state.limit + 1;
            var end = Math.min(state.page * state.limit, state.total);
            document.getElementById('pageInfo').textContent = 'Showing ' + start + '-' + end + ' of ' + state.total;
            document.getElementById('prevBtn').disabled = state.page <= 1;
            document.getElementById('nextBtn').disabled = state.page >= state.totalPages;
        }

        document.getElementById('prevBtn').onclick = function() {
            if (state.page > 1) { state.page--; loadData(); }
        };
        document.getElementById('nextBtn').onclick = function() {
            if (state.page < state.totalPages) { state.page++; loadData(); }
        };

        loadDatabases();
    </script>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Log HTTP requests."""
        print(f"  {args[0]} {args[1]} {args[2]}")


if __name__ == "__main__":
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
    print(f"Database viewer running at {url}")
    print("Press Ctrl+C to stop")

    timer = Timer(1.0, lambda: webbrowser.open(url))
    timer.daemon = True
    timer.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
