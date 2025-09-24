from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

jump_count = 0
last_jump_distance = 0.0
max_jump_distance = 0.0

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Broad Jump Counter</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>Broad Jump Counter</h1>
        <p id="count">Jump Count: <span>{{ jump_count }}</span></p>
        <p id="distance">Last Jump Distance: <span>{{ '{:.2f}'.format(last_jump_distance) }}</span> cm</p>
        <p id="max-distance">Highest Jump: <span>{{ '{:.2f}'.format(max_jump_distance) }}</span> cm</p>
    </div>
    <script>
        setInterval(function() {
            fetch('/status').then(r => r.json()).then(data => {
                document.querySelector("#count span").textContent = data.jump_count;
                document.querySelector("#distance span").textContent = Number(data.last_jump_distance).toFixed(2);
                document.querySelector("#max-distance span").textContent = Number(data.max_jump_distance).toFixed(2);
            });
        }, 1000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML, jump_count=jump_count, last_jump_distance=last_jump_distance, max_jump_distance=max_jump_distance)

@app.route('/status')
def status():
    return jsonify(jump_count=jump_count, last_jump_distance=last_jump_distance, max_jump_distance=max_jump_distance)

@app.route('/increment', methods=['POST'])
def increment():
    global jump_count, last_jump_distance, max_jump_distance
    data = request.get_json()
    jump_count += 1
    if data and "jump_height" in data:
        last_jump_distance = data["jump_height"]
        if last_jump_distance > max_jump_distance:
            max_jump_distance = last_jump_distance
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True)