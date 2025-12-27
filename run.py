from app import create_app, setup_database

app = create_app()

if __name__ == '__main__':
    # create DB and seed admin if not present
    setup_database(app)

    # run dev server
    app.run(debug=True)
