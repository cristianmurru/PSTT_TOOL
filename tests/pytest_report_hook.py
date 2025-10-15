import pytest
import time
from datetime import datetime
import os

def pytest_sessionfinish(session, exitstatus):
    # Recupera risultati
    results = []
    for item in session.items:
        duration = getattr(item, 'duration', None)
        results.append({
            'name': item.nodeid,
            'outcome': item._report_sections[0][2] if item._report_sections else 'unknown',
            'duration': duration if duration else 'N/A'
        })
    # Crea report Markdown
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = os.path.join(os.path.dirname(__file__), f'verbale_test_{timestamp}.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f'# Verbale Test - {timestamp}\n\n')
        for r in results:
            f.write(f'- **{r["name"]}**: {r["outcome"]} (Durata: {r["duration"]})\n')
        f.write(f'\n**Exit status:** {exitstatus}\n')

# Hook pytest
pytest.hookimpl(trylast=True)(pytest_sessionfinish)
