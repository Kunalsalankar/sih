from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

jump_count = 0
last_jump_height = 0.0
max_jump_height = 0.0

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Vertical Jump Counter</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>Vertical Jump Counter</h1>
        <p id="count">Jump Count: <span>{{ jump_count }}</span></p>
        <p id="height">Last Jump Height: <span>{{ '{:.2f}'.format(last_jump_height) }}</span> cm</p>
        <p id="max-height">Highest Jump: <span>{{ '{:.2f}'.format(max_jump_height) }}</span> cm</p>
    </div>
    <script>
        setInterval(function() {
            fetch('/status').then(r => r.json()).then(data => {
                document.querySelector("#count span").textContent = data.jump_count;
                document.querySelector("#height span").textContent = Number(data.last_jump_height).toFixed(2);
                document.querySelector("#max-height span").textContent = Number(data.max_jump_height).toFixed(2);
            });
        }, 1000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(
        HTML,
        jump_count=jump_count,
        last_jump_height=last_jump_height,
        max_jump_height=max_jump_height
    )

@app.route('/status')
def status():
    return jsonify(
        jump_count=jump_count,
        last_jump_height=last_jump_height,
        max_jump_height=max_jump_height
    )

@app.route('/increment', methods=['POST'])
def increment():
    global jump_count, last_jump_height, max_jump_height
    data = request.get_json()
    jump_count += 1
    if data and "jump_height" in data:
        last_jump_height = data["jump_height"]
        if last_jump_height > max_jump_height:
            max_jump_height = last_jump_height
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True)