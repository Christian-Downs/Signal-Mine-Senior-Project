from flask import Flask, request, jsonify

app = Flask(__name__)

# Example functions you want to expose
def call_ai_one(data):
    return {"message": f"AI One received: {data}"}

def call_ai_two(data):
    return {"message": f"AI Two received: {data}"}

# Simple registry of functions
FUNCTIONS = {
    "ai_one": call_ai_one,
    "ai_two": call_ai_two
}

@app.route("/invoke/<func_name>", methods=["POST"])
def invoke(func_name):
    if func_name not in FUNCTIONS:
        return jsonify({"error": "Function not found"}), 404

    payload = request.get_json(force=True)
    data = payload.get("data", {})

    try:
        result = FUNCTIONS[func_name](data)
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/health")
def health():
    return {"status": "up"}

if __name__ == "__main__":
    app.run(debug=True)
