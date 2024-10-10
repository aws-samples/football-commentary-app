import json
import os

api_url = os.environ.get('API_URL')


def handler(event, context):
    html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>⚽️ Latest Commentary ⚽️</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <script>
                tailwind.config = {{
                    theme: {{
                        extend: {{
                            animation: {{
                                'spin-slow': 'spin 10s linear infinite',
                            }}
                        }}
                    }}
                }}
            </script>
            <style type="text/tailwindcss">
                @layer utilities {{
                    .animate-spin-slow {{
                        animation: spin 10s linear infinite;
                    }}
                }}
            </style>
            <script>
                const apiUrl = "{api_url}/display";
                function fetchData() {{
                    fetch(apiUrl)
                        .then(response => response.json())
                        .then(data => {{
                            const comment = data.comment || 'No Commentary yet available';
                            const timestamp = data.timestamp || 'No Timestamp available';
                            document.getElementById('output').textContent = JSON.stringify(data, null, 2);
                        }})
                        .catch(error => console.error('Error:', error));
                }}
                // Fetch data every 5 seconds
                setInterval(fetchData, 5000);
                // Initial fetch
                fetchData();
            </script>
        </head>
        <body class="bg-gray-100 min-h-screen flex items-center justify-center">
            <div class="p-8 rounded-lg shadow-md max-w-2xl w-full text-center bg-green-500">
                <h1 class="text-2xl font-bold mb-4 text-gray-800">📣 Latest Commentary 🏟️</h1>
                <div id="output" class="bg-gray-50 p-4 rounded border border-gray-200 font-mono text-sm overflow-auto max-h-96">
                    Loading...
                </div>
                <div class="text-2xl animate-spin-slow" aria-label="Data is updating in real-time">⚽️</div>
            </div>
        </body>
        </html>
    """

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': html_content
    }
