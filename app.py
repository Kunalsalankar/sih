from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

counter = 0
current_reach = 0.0
max_reach = 0.0

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Sit and Reach Counter</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>Sit and Reach Counter</h1>
        <p id="count">Successful Attempts: <span>{{ counter }}</span></p>
        <p id="current-reach">Current Reach: <span>{{ current_reach }}</span> cm</p>
        <p id="max-reach">Max Reach: <span>{{ max_reach }}</span> cm</p>
    </div>
    <script>
        setInterval(function() {
            fetch('/status').then(r => r.json()).then(data => {
                document.querySelector("#count span").textContent = data.counter;
                document.querySelector("#current-reach span").textContent = data.current_reach;
                document.querySelector("#max-reach span").textContent = data.max_reach;
            });
        }, 1000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML, counter=counter, current_reach=current_reach, max_reach=max_reach)

@app.route('/status')
def status():
    return jsonify(counter=counter, current_reach=current_reach, max_reach=max_reach)

@app.route('/increment', methods=['POST'])
def increment():
    global counter
    counter += 1
    return jsonify(success=True)

@app.route('/update_reach', methods=['POST'])
def update_reach():
    global current_reach, max_reach
    data = request.get_json()
    current_reach = data.get('current_reach', 0.0)
    max_reach = data.get('max_reach', 0.0)
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True)