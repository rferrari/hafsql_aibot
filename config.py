from dotenv import load_dotenv
import os

load_dotenv()

DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() == "true"

# Discord Configuration
DISCORD_CONFIG = {
    "token": os.environ.get("DISCORD_TOKEN"),
    "admin_id": os.environ.get("DISCORD_ADMIN_ID"),
    "cool_down_duration": 5,
    "max_daily_queries": 25
}

# Database Configuration
DB_CONFIG = {
    "server": os.environ.get("HAFSQL_SERVER"),
    "database": os.environ.get("HAFSQL_DATABASE"),
    "user": os.environ.get("HAFSQL_USER"),
    "password": os.environ.get("HAFSQL_PWD")
}

# LLM Configuration
LLM_CONFIG = {
    "groq_api_key": os.environ.get("GROQ_API_KEY", False),
    "openai_api_key": os.environ.get("OPENAI_API_KEY", False),
    "groq_model": os.environ.get("GROQ_LLM_MODEL", "gemma2-9b-it"),
    "openai_model": os.environ.get("OPENAI_LLM_MODEL", "gpt-4o-mini"),
    "eval_temp": float(os.environ.get("EVAL_TEMPERATURE", 0.7)),
    "query_temp": float(os.environ.get("QUERY_TEMPERATURE", 0.1)),
    "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", 1024))
}

# SQL Queries
SQL_QUERIES = {
    "select_tables": """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'hafsql'
    AND table_type = 'BASE TABLE';
    """,

    "select_views": """
    SELECT table_name
    FROM information_schema.views
    WHERE table_schema = 'hafsql';
    """,
    
    "create_tables_schema": """
    SELECT 
        'CREATE TABLE ' || table_name || ' (' ||
        COALESCE(STRING_AGG(
            column_name || ' ' || 
            CASE 
                WHEN data_type IN ('character varying', 'char') AND character_maximum_length IS NOT NULL THEN 
                    data_type || '(' || character_maximum_length || ')'
                ELSE 
                    COALESCE(data_type, 'UNKNOWN')
            END, ', '), 'NO COLUMNS'
        ) 
        || ');' AS create_table_ddl
    FROM information_schema.columns
    WHERE table_schema = 'hafsql' 
    GROUP BY table_name;
    """,

    "create_views_schema": """
    SELECT 
        'CREATE VIEW ' || table_name || ' (' || 
        STRING_AGG(
            column_name || ' ' || 
            CASE 
                WHEN data_type IN ('character varying', 'char') THEN 
                    data_type || '(' || character_maximum_length || ')'
                ELSE 
                    data_type
            END, ', '
        ) 
        || ');' AS create_table_ddl
    FROM information_schema.columns
    WHERE table_schema = 'hafsql' 
    AND table_name IN (
        SELECT table_name FROM information_schema.views WHERE table_schema = 'hafsql'
    )
    GROUP BY table_name;
    """
}
# SQL_QUERIES = {
#     "select_tables": "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS;",
    
#     "create_tables_schema": """
#     SELECT 
#         'CREATE TABLE ' + '' + TABLE_NAME + ' (' +
#         STRING_AGG(COLUMN_NAME, ', ') + ');' AS CreateTableDDL
#     FROM INFORMATION_SCHEMA.COLUMNS
#     GROUP BY TABLE_SCHEMA, TABLE_NAME;
#     """,

#     "create_views_schema": """
#     SELECT 
#     'CREATE TABLE ' +TABLE_NAME + ' (' + 
#     STRING_AGG(COLUMN_NAME + ' ' + DATA_TYPE + 
#         COALESCE('(' + CAST(CHARACTER_MAXIMUM_LENGTH AS VARCHAR) + ')', ''), ', ') 
#     + ');' AS CreateTableDDL
#     FROM INFORMATION_SCHEMA.COLUMNS
#     GROUP BY TABLE_SCHEMA, TABLE_NAME;
#     """
# }

SKIP_TABLES = [
    # "accounts_table",
    # "balances_history_table",
    # "balances_table",
    # "blacklist_follows_table",
    # "blacklists_table",
    # "comments_table",
    # "community_roles_table",
    # "community_subs_table",
    # "delegations_table",
    # "follows_table",
    "market_bucket_1d_table",
    "market_bucket_1h_table",
    "market_bucket_1w_table",
    "market_bucket_30m_table",
    "market_bucket_4h_table",
    "market_bucket_4w_table",
    "market_bucket_5m_table",
    "market_open_orders_table",
    "mute_follows_table",
    "mutes_table",
    "operation_account_create_table",
    "operation_account_create_with_delegation_table",
    "operation_account_created_table",
    "operation_account_update2_table",
    "operation_account_update_table",
    "operation_account_witness_proxy_table",
    "operation_account_witness_vote_table",
    "operation_author_reward_table",
    "operation_cancel_transfer_from_savings_table",
    "operation_change_recovery_account_table",
    "operation_changed_recovery_account_table",
    "operation_claim_account_table",
    "operation_claim_reward_balance_table",
    "operation_clear_null_account_balance_table",
    "operation_collateralized_convert_immediate_conversion_table",
    "operation_collateralized_convert_table",
    "operation_comment_benefactor_reward_table",
    "operation_comment_options_table",
    "operation_comment_payout_update_table",
    "operation_comment_reward_table",
    "operation_consolidate_treasury_balance_table",
    "operation_convert_table",
    "operation_create_claimed_account_table",
    # "operation_create_proposal_table",
    "operation_curation_reward_table",
    "operation_custom_table",
    "operation_decline_voting_rights_table",
    "operation_delayed_voting_table",
    "operation_delegate_vesting_shares_table",
    "operation_delete_comment_table",
    "operation_dhf_conversion_table",
    "operation_dhf_funding_table",
    "operation_escrow_approve_table",
    "operation_escrow_approved_table",
    "operation_escrow_dispute_table",
    "operation_escrow_rejected_table",
    "operation_escrow_release_table",
    "operation_escrow_transfer_table",
    "operation_expired_account_notification_table",
    "operation_failed_recurrent_transfer_table",
    "operation_feed_publish_table",
    "operation_fill_collateralized_convert_request_table",
    "operation_fill_convert_request_table",
    "operation_fill_order_table",
    "operation_fill_recurrent_transfer_table",
    "operation_fill_transfer_from_savings_table",
    "operation_fill_vesting_withdraw_table",
    "operation_hardfork_hive_restore_table",
    "operation_hardfork_hive_table",
    "operation_hardfork_table",
    "operation_ineffective_delete_comment_table",
    "operation_interest_table",
    "operation_limit_order_cancel_table",
    "operation_limit_order_cancelled_table",
    "operation_limit_order_create2_table",
    "operation_limit_order_create_table",
    "operation_liquidity_reward_table",
    "operation_pow2_table",
    "operation_pow_reward_table",
    "operation_pow_table",
    "operation_producer_missed_table",
    "operation_producer_reward_table",
    # "operation_proposal_fee_table",
    # "operation_proposal_pay_table",
    "operation_proxy_cleared_table",
    "operation_recover_account_table",
    "operation_recurrent_transfer_table",
    # "operation_remove_proposal_table",
    "operation_request_account_recovery_table",
    "operation_return_vesting_delegation_table",
    "operation_set_withdraw_vesting_route_table",
    "operation_shutdown_witness_table",
    "operation_system_warning_table",
# "operation_transfer_from_savings_table",
# "operation_transfer_table",
# "operation_transfer_to_savings_table",
# "operation_transfer_to_vesting_completed_table",
# "operation_transfer_to_vesting_table",
    # "operation_update_proposal_table",
    # "operation_update_proposal_votes_table",
    "operation_vesting_shares_split_table",
    "operation_withdraw_vesting_table",
    "operation_witness_set_properties_table",
    "operation_witness_update_table",
# "pending_saving_withdraws_table",
# "proposal_approvals_table",
# "rc_delegations_table",
# "reblogs_table",
# "reputations_table",
    "sync_data",
# "total_balances_table",
    "version"
]
