from config import clear_env_cache

if __name__ == "__main__":
    print("Clearing environment variable caches...")
    settings = clear_env_cache()
    print("Environment variables reloaded successfully!")
    print("\nCurrent settings:")
    for field in settings.__fields__:
        if not field.startswith("_"):
            value = getattr(settings, field)
            # Don't print sensitive values
            if field in ["email_password", "secret_key", "openai_api_key"]:
                value = "***" if value else "Not set"
            print(f"{field}: {value}")
