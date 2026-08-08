import json
import logging
from ..core.redis import redis_client
from ..core.constants import REDIS_OAUTH_CRED_PREFIX

logger = logging.getLogger(__name__)

async def get_last_seen_autoid(
    phone_number_id: str, 
    systemid: str, 
):
    """Get last seen auto ID from existing auth cred record"""
    try:
        redis_key = f"{REDIS_OAUTH_CRED_PREFIX}{phone_number_id}"
        existing_data = await redis_client.get(redis_key)

        if not existing_data:
            return 0
        
        cred_data = json.loads(existing_data)
        
        # Build criteria identifier
        criteria_parts = [systemid]
        criteria_key = ":".join(criteria_parts)
        
        # Navigate to webhook tracking
        if "webhook_tracking" not in cred_data:
            return 0
        
        return cred_data["webhook_tracking"].get(criteria_key, 0)
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON for {phone_number_id}: {e}")
        return 0
    except Exception as e:
        logger.error(f"Error getting last seen autoid for {phone_number_id}: {e}")
        return 0


async def update_last_seen_autoid(
    phone_number_id: str, 
    systemid: str, 
    autoid: int, 
):
    """Update last seen auto ID in existing auth cred record"""
    try:
        redis_key = f"{REDIS_OAUTH_CRED_PREFIX}{phone_number_id}"
        
        # Get existing data or create new
        existing_data = await redis_client.get(redis_key)
        if existing_data:
            cred_data = json.loads(existing_data)
        else:
            cred_data = {}
        
        # Build criteria identifier
        criteria_parts = [systemid]
        criteria_key = ":".join(criteria_parts)
        
        # Initialize webhook_tracking if not exists
        if "webhook_tracking" not in cred_data:
            cred_data["webhook_tracking"] = {}
        
        # Update last seen for this criteria
        cred_data["webhook_tracking"][criteria_key] = autoid
        
        await redis_client.set(redis_key, json.dumps(cred_data))
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON for {phone_number_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error updating last seen autoid for {phone_number_id}: {e}")
        raise


async def query_webhooks(
    phone_number_id: str, 
    systemid: str, 
    limit=100
):
    """Query webhooks from last seen position"""
    try:
        # Get last seen auto ID
        last_seen = await get_last_seen_autoid(
            phone_number_id= phone_number_id, 
            systemid = systemid, 
        )
        
        # Build query
        conditions = [
            f"@autoid:[{last_seen + 1} +inf]",
            f"@phone_number_id:{{{phone_number_id}}}"
        ]
        
        query = " ".join(conditions)
        
        # Search with sorting by autoid ASC (oldest to recent)
        results = await redis_client.execute_command(
            'FT.SEARCH', 'idx:wawebhooks',
            query,
            'SORTBY', 'autoid', 'ASC',
            'LIMIT', '0', str(limit)
        )
        
        # Parse RediSearch results
        data = []
        max_autoid = last_seen
        
        total_results = int(results[0])
        
        if total_results > 0:
            # Skip first element (count) and iterate pairs
            i = 1
            while i < len(results):
                try:
                    key = results[i]
                    fields = results[i + 1]
                    
                    # Convert list of [field, value, field, value] to dict
                    item = {}
                    for j in range(0, len(fields), 2):
                        field_name = fields[j]
                        field_value = fields[j + 1]
                        item[field_name] = field_value
                    
                    item['autoid'] = int(item['autoid'])
                    item['previousattachments'] = json.loads(item.get('previousattachments', '[]'))
                    item['currentattachments'] = json.loads(item.get('currentattachments', '[]'))
                    data.append(item)
                    
                    # Track highest autoid
                    max_autoid = max(max_autoid, item['autoid'])
                    
                except (KeyError, ValueError, json.JSONDecodeError) as e:
                    logger.warning(f"Failed to parse webhook result: {e}")
                    # Skip this result and continue
                
                i += 2  # Move to next result
        
        # Update last seen
        if data:
            try:
                await update_last_seen_autoid(
                    phone_number_id=phone_number_id, 
                    systemid = systemid,
                    autoid=max_autoid)
            except Exception as e:
                logger.error(f"Failed to update last seen, but returning data anyway: {e}")
                # Don't fail the query if tracking update fails
        
        return data
    
    except Exception as e:
        logger.error(f"Error querying webhooks for {phone_number_id}: {e}")
        raise