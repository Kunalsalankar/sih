from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

counter = 0

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Sit-up Counter</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>Sit-up Counter</h1>
        <p id="count">Successful Sit-ups: <span>{{ counter }}</span></p>
    </div>
    <script>
        setInterval(function() {
            fetch('/status').then(r => r.json()).then(data => {
                document.querySelector("#count span").textContent = data.counter;
            });
        }, 1000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML, counter=counter)

@app.route('/status')
def status():
    return jsonify(counter=counter)

@app.route('/increment', methods=['POST'])
def increment():
    global counter
    counter += 1
    return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True)

app.py