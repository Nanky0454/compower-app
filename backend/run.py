from app import create_app

app = create_app()

if __name__ == '__main__':
    # Force reload v11 - RENIEC Integration
    app.run(debug=True, port=5000)