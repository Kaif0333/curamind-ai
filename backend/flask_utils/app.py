from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
def index():
    return """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>CuraMind Utils</title>
        <style>
            body {
                margin: 0;
                font-family: "Segoe UI", sans-serif;
                background: linear-gradient(180deg, #f7fbfb 0%, #edf3f2 100%);
                color: #16353f;
            }
            main {
                width: min(760px, calc(100vw - 2rem));
                margin: 4rem auto;
                padding: 2rem;
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(22, 53, 63, 0.12);
                border-radius: 24px;
                box-shadow: 0 24px 60px rgba(22, 53, 63, 0.12);
            }
            h1 {
                font-size: clamp(2rem, 5vw, 3rem);
                margin-bottom: 0.5rem;
            }
            p {
                line-height: 1.6;
                color: #49646c;
            }
            .links {
                display: grid;
                gap: 1rem;
                margin-top: 1.5rem;
            }
            a {
                display: block;
                padding: 1rem 1.1rem;
                border-radius: 16px;
                text-decoration: none;
                color: inherit;
                background: #f5fbfa;
                border: 1px solid rgba(22, 53, 63, 0.1);
                font-weight: 600;
            }
            code {
                display: block;
                margin-top: 0.35rem;
                color: #5d777f;
            }
        </style>
    </head>
    <body>
        <main>
            <h1>CuraMind Utils</h1>
            <p>Lightweight operational endpoints for local health checks and service metadata.</p>
            <div class="links">
                <a href="/health">Health check <code>GET /utils/health</code></a>
                <a href="/version">Service version <code>GET /utils/version</code></a>
            </div>
        </main>
    </body>
    </html>
    """


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/version")
def version():
    return jsonify({"service": "curamind-utils", "version": "1.0.0"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002)
