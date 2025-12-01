import os
from flask import Flask
from .config import Config
from .extensions import db, migrate, jwt


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)

    if test_config is not None:
        app.config.update(test_config)

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # register blueprints
    from .routes import register_blueprints

    register_blueprints(app)

    # CLI commands
    @app.cli.command()
    def init_db():
        """Initialize the database tables and load languages."""
        import json
        from pathlib import Path
        
        try:
            db.create_all()
            print("✓ Database tables created successfully")
            
            # Import languages from JSON
            from .models import Language
            
            # Check if languages already loaded
            if Language.query.first() is None:
                lang_file = Path(__file__).parent.parent / 'import' / 'languages.json'
                if lang_file.exists():
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        languages = json.load(f)
                    
                    for lang in languages:
                        language = Language(code=lang['alpha2'], name=lang['English'])
                        db.session.add(language)
                    
                    db.session.commit()
                    print(f"✓ Loaded {len(languages)} languages")
                else:
                    print("⚠ Warning: languages.json not found")
            else:
                print("✓ Languages already loaded")
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error during initialization: {e}")
            raise

    return app

