"""HTML export for evaluation results."""

import argparse
import json
from pathlib import Path
from datetime import datetime

from review_aggregator.eval.db import get_batch_stats, get_llm_outputs, get_judge_scores
from review_aggregator.utils.logger import get_logger

logger = get_logger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"


def generate_html_report(batch_id: str) -> str:
    """
    Generate HTML report for a batch.

    Returns HTML string.
    """
    stats = get_batch_stats(batch_id)
    if not stats:
        raise ValueError(f"Batch {batch_id} not found")

    outputs = get_llm_outputs(batch_id=batch_id)

    # Calculate field accuracy
    field_accuracy = stats.get("field_accuracy", {})

    # HTML template
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Eval Report - {batch_id}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; margin-bottom: 10px; font-size: 28px; }}
        .subtitle {{ color: #666; margin-bottom: 30px; font-size: 14px; }}
        .meta {{ background: #f9f9f9; padding: 15px; border-radius: 4px; margin-bottom: 30px; }}
        .meta-item {{ margin: 8px 0; color: #555; }}
        .meta-label {{ color: #999; font-size: 12px; text-transform: uppercase; }}

        .section {{ margin-bottom: 40px; }}
        .section-title {{ color: #333; font-size: 20px; font-weight: 600; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #eee; }}

        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .metric {{ background: #f9f9f9; padding: 20px; border-radius: 4px; border-left: 4px solid #4CAF50; }}
        .metric-value {{ font-size: 28px; font-weight: bold; color: #4CAF50; }}
        .metric-label {{ color: #666; font-size: 12px; text-transform: uppercase; margin-top: 5px; }}

        .accuracy-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }}
        .accuracy-bar {{ background: #f0f0f0; border-radius: 4px; padding: 12px; }}
        .accuracy-label {{ font-size: 12px; color: #666; margin-bottom: 8px; }}
        .accuracy-value {{ font-size: 18px; font-weight: bold; color: #333; }}
        .progress-bar {{ width: 100%; height: 6px; background: #e0e0e0; border-radius: 3px; margin-top: 8px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: #4CAF50; border-radius: 3px; }}

        .model-results {{ background: #f9f9f9; padding: 15px; border-radius: 4px; margin-bottom: 15px; }}
        .model-name {{ font-weight: 600; color: #333; margin-bottom: 8px; }}
        .model-count {{ color: #999; font-size: 12px; }}

        .score-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        .score-table th, .score-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        .score-table th {{ background: #f5f5f5; font-weight: 600; color: #333; font-size: 12px; }}
        .score-table td {{ font-size: 14px; }}
        .score-table tbody tr:hover {{ background: #fafafa; }}

        .score-badge {{ display: inline-block; padding: 4px 8px; border-radius: 3px; font-size: 12px; font-weight: 600; }}
        .score-1 {{ background: #e8f5e9; color: #2e7d32; }}
        .score-0 {{ background: #ffebee; color: #c62828; }}

        .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; }}

        .empty {{ color: #999; text-align: center; padding: 40px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Evaluation Report</h1>
        <div class="subtitle">Batch ID: {batch_id}</div>

        <div class="meta">
            <div class="meta-item"><span class="meta-label">Created</span> {stats.get('created_at', 'N/A')}</div>
            <div class="meta-item"><span class="meta-label">Mode</span> {stats.get('sample_mode', 'N/A')}</div>
            <div class="meta-item"><span class="meta-label">Critic</span> {stats.get('critic_id', 'All')}</div>
        </div>

        <!-- Summary Section -->
        <div class="section">
            <div class="section-title">Summary</div>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{stats.get('sample_count', 0)}</div>
                    <div class="metric-label">Samples</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{stats.get('output_count', 0)}</div>
                    <div class="metric-label">Outputs</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{stats.get('score_count', 0)}</div>
                    <div class="metric-label">Scores</div>
                </div>
            </div>
        </div>

        <!-- Model Results -->
        {generate_model_results_html(stats)}

        <!-- Field Accuracy -->
        {generate_field_accuracy_html(field_accuracy)}

        <!-- Output Details Table -->
        {generate_outputs_table_html(outputs)}

        <div class="footer">
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""

    return html


def generate_model_results_html(stats: dict) -> str:
    """Generate model results section."""
    model_counts = stats.get("model_counts", {})

    if not model_counts:
        return ""

    html = '<div class="section"><div class="section-title">Models</div>'

    for model, count in model_counts.items():
        html += f"""<div class="model-results">
            <div class="model-name">{model}</div>
            <div class="model-count">{count} outputs</div>
        </div>"""

    html += '</div>'
    return html


def generate_field_accuracy_html(field_accuracy: dict) -> str:
    """Generate field accuracy section."""
    if not field_accuracy:
        return ""

    html = '<div class="section"><div class="section-title">Field Accuracy</div><div class="accuracy-grid">'

    for field, accuracy in field_accuracy.items():
        percent = round(accuracy * 100, 1)
        html += f"""<div class="accuracy-bar">
            <div class="accuracy-label">{field.replace('_', ' ').title()}</div>
            <div class="accuracy-value">{percent}%</div>
            <div class="progress-bar"><div class="progress-fill" style="width: {percent}%"></div></div>
        </div>"""

    html += '</div></div>'
    return html


def generate_outputs_table_html(outputs: list) -> str:
    """Generate outputs table."""
    if not outputs:
        return '<div class="section"><div class="empty">No outputs to display</div></div>'

    html = """<div class="section">
        <div class="section-title">Output Details</div>
        <table class="score-table">
            <thead>
                <tr>
                    <th>Model</th>
                    <th>Prompt Version</th>
                    <th>Film Review</th>
                    <th>Sentiment</th>
                    <th>Latency (ms)</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>"""

    for output in outputs[:100]:  # Limit to first 100
        is_film_review = output.get("output_is_film_review")
        sentiment = output.get("output_sentiment", "N/A")
        latency = output.get("latency_ms")
        error = output.get("error")

        if error:
            status_html = '<span class="score-badge score-0">Error</span>'
        else:
            status_html = '<span class="score-badge score-1">Success</span>'

        if is_film_review is not None:
            film_badge = f'<span class="score-badge score-{"1" if is_film_review else "0"}">{"Yes" if is_film_review else "No"}</span>'
        else:
            film_badge = "N/A"

        latency_str = f"{latency:.0f}" if latency else "N/A"

        html += f"""<tr>
            <td>{output.get('model', 'N/A')}</td>
            <td>{output.get('prompt_version', 'N/A')}</td>
            <td>{film_badge}</td>
            <td>{sentiment}</td>
            <td>{latency_str}</td>
            <td>{status_html}</td>
        </tr>"""

    html += """</tbody>
        </table>
    </div>"""

    return html


def export_to_html(batch_id: str, output_path: str = None) -> Path:
    """
    Export batch results to HTML.

    Args:
        batch_id: Batch ID
        output_path: Optional output file path

    Returns:
        Path to generated HTML file
    """
    if output_path is None:
        RESULTS_DIR.mkdir(exist_ok=True)
        output_path = RESULTS_DIR / f"report_{batch_id[:8]}.html"
    else:
        output_path = Path(output_path)

    html = generate_html_report(batch_id)

    with open(output_path, "w") as f:
        f.write(html)

    logger.info(f"Exported report to {output_path}")
    return output_path


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Export evaluation results to HTML")
    parser.add_argument("batch_id", help="Batch ID")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    path = export_to_html(args.batch_id, args.output)
    print(f"Report saved to: {path}")


if __name__ == "__main__":
    main()
