from typing import Dict, Any
import os

def validate_env_config() -> Dict[str, Any]:
    """Validate and return environment configuration"""
    required_vars = {
        'CHANNEL_ID': str,
        'TIMESTAMP_COMMENTERS': str,
        'KEYWORDS': str,
        'UPLOAD_PRIVACY': lambda x: x in ['private', 'unlisted', 'public'],
        'UPLOAD_TIMES': lambda x: all(':' in t for t in x.split(','))
    }
    
    config = {}
    missing = []
    invalid = []
    
    for var, validator in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing.append(var)
            continue
            
        try:
            if callable(validator):
                if not validator(value):
                    invalid.append(var)
                else:
                    config[var] = value
            elif not isinstance(value, validator):
                invalid.append(var)
            else:
                config[var] = value
        except:
            invalid.append(var)
    
    if missing or invalid:
        raise ValueError(
            f"Configuration error!\n"
            f"Missing variables: {', '.join(missing)}\n"
            f"Invalid variables: {', '.join(invalid)}"
        )
    
    return config 