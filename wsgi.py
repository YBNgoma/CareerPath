from app import app

# This is the WSGI entry point for the clinic management application
# The variable 'app' will be used as specified in DirectAdmin settings
if __name__ == "__main__":
    app.run()