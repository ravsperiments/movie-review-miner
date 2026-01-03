"""Interactive HTML viewer for model scores across batches."""

import argparse
import json
from pathlib import Path
from datetime import datetime

from review_aggregator.eval.db import get_eval_db
from review_aggregator.eval.judge import get_model_scores, SCORE_FIELDS
from review_aggregator.utils.logger import get_logger

logger = get_logger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"


def get_all_batches() -> list[dict]:
    """Get all batches with basic info."""
    db = get_eval_db()
    query = """
        SELECT
            sb.id,
            sb.critic_id,
            sb.sample_size,
            sb.sample_mode,
            sb.created_at,
            COUNT(DISTINCT s.id) as sample_count,
            COUNT(DISTINCT lo.id) as output_count,
            COUNT(DISTINCT js.id) as score_count
        FROM sample_batches sb
        LEFT JOIN samples s ON s.batch_id = sb.id
        LEFT JOIN llm_outputs lo ON lo.sample_id = s.id
        LEFT JOIN judge_scores js ON js.llm_output_id = lo.id
        GROUP BY sb.id
        ORDER BY sb.created_at DESC
    """
    return db.execute_query(query, fetch=True)


def get_all_batch_scores() -> dict:
    """Get model scores for all batches."""
    batches = get_all_batches()
    batch_scores = {}

    for batch in batches:
        batch_id = batch["id"]
        scores = get_model_scores(batch_id)
        batch_scores[batch_id] = {
            "info": batch,
            "scores": scores,
        }

    return batch_scores


def generate_scores_html() -> str:
    """Generate interactive HTML for viewing model scores."""
    batch_scores = get_all_batch_scores()

    # Prepare data for JavaScript
    batches_json = json.dumps(batch_scores, default=str, indent=2)
    fields_json = json.dumps(SCORE_FIELDS)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Model Scores - Eval Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0f0f0f;
            color: #e0e0e0;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px;
        }}

        h1 {{
            color: #fff;
            font-size: 32px;
            font-weight: 600;
            margin-bottom: 8px;
        }}

        .subtitle {{
            color: #888;
            font-size: 14px;
            margin-bottom: 30px;
        }}

        /* Batch selector */
        .batch-selector {{
            background: #1a1a1a;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            border: 1px solid #2a2a2a;
        }}

        .batch-selector label {{
            display: block;
            color: #888;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }}

        .batch-selector select {{
            width: 100%;
            padding: 12px 16px;
            font-size: 14px;
            background: #0f0f0f;
            border: 1px solid #333;
            border-radius: 8px;
            color: #e0e0e0;
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23888' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 16px center;
        }}

        .batch-selector select:focus {{
            outline: none;
            border-color: #4CAF50;
        }}

        /* Batch info */
        .batch-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #2a2a2a;
        }}

        .info-item {{
            text-align: center;
        }}

        .info-value {{
            font-size: 24px;
            font-weight: 600;
            color: #fff;
        }}

        .info-label {{
            font-size: 11px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 4px;
        }}

        /* Model comparison table */
        .table-container {{
            background: #1a1a1a;
            border-radius: 12px;
            border: 1px solid #2a2a2a;
            overflow: hidden;
        }}

        .table-header {{
            padding: 20px;
            border-bottom: 1px solid #2a2a2a;
        }}

        .table-title {{
            font-size: 18px;
            font-weight: 600;
            color: #fff;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            text-align: left;
            padding: 14px 16px;
            font-size: 11px;
            font-weight: 600;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background: #151515;
            border-bottom: 1px solid #2a2a2a;
        }}

        th.score-col {{
            text-align: right;
        }}

        td {{
            padding: 16px;
            font-size: 14px;
            border-bottom: 1px solid #222;
        }}

        tr:hover td {{
            background: #1f1f1f;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        .model-name {{
            font-weight: 500;
            color: #fff;
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .score-cell {{
            text-align: right;
            font-family: "SF Mono", Monaco, monospace;
            font-size: 13px;
        }}

        .score-high {{ color: #4CAF50; }}
        .score-mid {{ color: #FFC107; }}
        .score-low {{ color: #f44336; }}

        .overall-score {{
            font-weight: 600;
            font-size: 14px;
        }}

        .sample-count {{
            color: #666;
            font-size: 12px;
            text-align: center;
        }}

        /* Average row */
        tr.average-row td {{
            background: #1f1f1f;
            border-top: 2px solid #333;
            font-weight: 600;
        }}

        tr.average-row .model-name {{
            color: #888;
        }}

        /* Progress bar in cells */
        .score-bar {{
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 10px;
        }}

        .bar {{
            width: 60px;
            height: 4px;
            background: #333;
            border-radius: 2px;
            overflow: hidden;
        }}

        .bar-fill {{
            height: 100%;
            border-radius: 2px;
            transition: width 0.3s ease;
        }}

        .bar-fill.high {{ background: #4CAF50; }}
        .bar-fill.mid {{ background: #FFC107; }}
        .bar-fill.low {{ background: #f44336; }}

        /* Empty state */
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }}

        .empty-state svg {{
            width: 48px;
            height: 48px;
            margin-bottom: 16px;
            opacity: 0.5;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            color: #444;
            font-size: 12px;
            margin-top: 40px;
            padding-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Model Scores</h1>
        <div class="subtitle">Compare model performance across evaluation batches</div>

        <div class="batch-selector">
            <label for="batch-select">Select Batch</label>
            <select id="batch-select" onchange="renderBatch(this.value)">
                <option value="">-- Select a batch --</option>
            </select>

            <div class="batch-info" id="batch-info" style="display: none;">
                <div class="info-item">
                    <div class="info-value" id="info-samples">-</div>
                    <div class="info-label">Samples</div>
                </div>
                <div class="info-item">
                    <div class="info-value" id="info-outputs">-</div>
                    <div class="info-label">Outputs</div>
                </div>
                <div class="info-item">
                    <div class="info-value" id="info-scores">-</div>
                    <div class="info-label">Scores</div>
                </div>
                <div class="info-item">
                    <div class="info-value" id="info-models">-</div>
                    <div class="info-label">Models</div>
                </div>
                <div class="info-item">
                    <div class="info-value" id="info-date">-</div>
                    <div class="info-label">Created</div>
                </div>
            </div>
        </div>

        <div class="table-container">
            <div class="table-header">
                <div class="table-title">Model Comparison</div>
            </div>
            <div id="table-content">
                <div class="empty-state">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                    <div>Select a batch to view model scores</div>
                </div>
            </div>
        </div>

        <div class="footer">
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>

    <script>
        const batchData = {batches_json};
        const scoreFields = {fields_json};

        const fieldLabels = {{
            'is_film_review': 'Is Review',
            'movie_names': 'Movies',
            'sentiment': 'Sentiment',
            'cleaned_title': 'Title',
            'cleaned_short_review': 'Summary'
        }};

        function init() {{
            const select = document.getElementById('batch-select');

            // Sort batches by date descending
            const sortedBatches = Object.entries(batchData)
                .sort((a, b) => new Date(b[1].info.created_at) - new Date(a[1].info.created_at));

            sortedBatches.forEach(([id, data]) => {{
                const info = data.info;
                const date = new Date(info.created_at).toLocaleDateString();
                const modelCount = Object.keys(data.scores.models || {{}}).length;
                const label = `${{date}} - ${{info.sample_count}} samples, ${{modelCount}} models (${{id.slice(0, 8)}})`;

                const option = document.createElement('option');
                option.value = id;
                option.textContent = label;
                select.appendChild(option);
            }});

            // Auto-select first batch if available
            if (sortedBatches.length > 0) {{
                select.value = sortedBatches[0][0];
                renderBatch(sortedBatches[0][0]);
            }}
        }}

        function getScoreClass(score) {{
            if (score >= 0.8) return 'high';
            if (score >= 0.5) return 'mid';
            return 'low';
        }}

        function formatScore(score) {{
            if (score === null || score === undefined) return 'N/A';
            return (score * 100).toFixed(1) + '%';
        }}

        function renderBatch(batchId) {{
            if (!batchId || !batchData[batchId]) {{
                document.getElementById('batch-info').style.display = 'none';
                document.getElementById('table-content').innerHTML = `
                    <div class="empty-state">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                        <div>Select a batch to view model scores</div>
                    </div>
                `;
                return;
            }}

            const data = batchData[batchId];
            const info = data.info;
            const scores = data.scores;

            // Update batch info
            document.getElementById('batch-info').style.display = 'grid';
            document.getElementById('info-samples').textContent = info.sample_count || 0;
            document.getElementById('info-outputs').textContent = info.output_count || 0;
            document.getElementById('info-scores').textContent = info.score_count || 0;
            document.getElementById('info-models').textContent = Object.keys(scores.models || {{}}).length;
            document.getElementById('info-date').textContent = new Date(info.created_at).toLocaleDateString();

            // Render table
            if (!scores.models || Object.keys(scores.models).length === 0) {{
                document.getElementById('table-content').innerHTML = `
                    <div class="empty-state">
                        <div>No scores available for this batch</div>
                    </div>
                `;
                return;
            }}

            // Sort models by overall score
            const sortedModels = Object.entries(scores.models)
                .sort((a, b) => (b[1].overall_score || 0) - (a[1].overall_score || 0));

            let tableHtml = `
                <table>
                    <thead>
                        <tr>
                            <th>Model</th>
                            ${{scoreFields.map(f => `<th class="score-col">${{fieldLabels[f] || f}}</th>`).join('')}}
                            <th class="score-col">Overall</th>
                            <th style="text-align: center;">N</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            sortedModels.forEach(([model, modelData]) => {{
                tableHtml += `<tr>`;
                tableHtml += `<td class="model-name" title="${{model}}">${{model}}</td>`;

                scoreFields.forEach(field => {{
                    const score = modelData.field_scores[field];
                    const scoreClass = getScoreClass(score);
                    tableHtml += `
                        <td class="score-cell">
                            <div class="score-bar">
                                <span class="score-${{scoreClass}}">${{formatScore(score)}}</span>
                                <div class="bar">
                                    <div class="bar-fill ${{scoreClass}}" style="width: ${{(score || 0) * 100}}%"></div>
                                </div>
                            </div>
                        </td>
                    `;
                }});

                const overallClass = getScoreClass(modelData.overall_score);
                tableHtml += `
                    <td class="score-cell overall-score score-${{overallClass}}">
                        ${{formatScore(modelData.overall_score)}}
                    </td>
                    <td class="sample-count">${{modelData.sample_count}}</td>
                </tr>`;
            }});

            // Average row
            if (scores.field_averages) {{
                const avgScores = scoreFields.map(f => scores.field_averages[f] || 0);
                const overallAvg = avgScores.reduce((a, b) => a + b, 0) / avgScores.length;

                tableHtml += `<tr class="average-row">`;
                tableHtml += `<td class="model-name">AVERAGE</td>`;

                scoreFields.forEach(field => {{
                    const score = scores.field_averages[field];
                    const scoreClass = getScoreClass(score);
                    tableHtml += `
                        <td class="score-cell">
                            <div class="score-bar">
                                <span class="score-${{scoreClass}}">${{formatScore(score)}}</span>
                                <div class="bar">
                                    <div class="bar-fill ${{scoreClass}}" style="width: ${{(score || 0) * 100}}%"></div>
                                </div>
                            </div>
                        </td>
                    `;
                }});

                const overallClass = getScoreClass(overallAvg);
                tableHtml += `
                    <td class="score-cell overall-score score-${{overallClass}}">
                        ${{formatScore(overallAvg)}}
                    </td>
                    <td class="sample-count">-</td>
                </tr>`;
            }}

            tableHtml += `</tbody></table>`;
            document.getElementById('table-content').innerHTML = tableHtml;
        }}

        // Initialize on load
        init();
    </script>
</body>
</html>"""

    return html


def export_scores_html(output_path: str = None) -> Path:
    """
    Export model scores viewer to HTML.

    Args:
        output_path: Optional output file path

    Returns:
        Path to generated HTML file
    """
    if output_path is None:
        RESULTS_DIR.mkdir(exist_ok=True)
        output_path = RESULTS_DIR / "scores.html"
    else:
        output_path = Path(output_path)

    html = generate_scores_html()

    with open(output_path, "w") as f:
        f.write(html)

    logger.info(f"Exported scores to {output_path}")
    return output_path


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate HTML viewer for model scores")
    parser.add_argument("--output", "-o", help="Output file path")
    parser.add_argument("--open", action="store_true", help="Open in browser after generating")
    args = parser.parse_args()

    path = export_scores_html(args.output)
    print(f"Scores viewer saved to: {path}")

    if args.open:
        import webbrowser
        webbrowser.open(f"file://{path.absolute()}")


if __name__ == "__main__":
    main()
