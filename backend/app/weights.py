FLAG_WEIGHTS = {
    # data_collection (low)
    "uses_cookies": 1,
    "collects_ip_address": 2,
    "collects_device_info": 2,
    "collects_location": 3,
    "collects_email_address": 2,
    "collects_birthday": 2,

    # advertising (medium)
    "collects_behavioral_data": 4,
    "uses_cross_site_tracking": 6,
    "uses_targeted_ads": 5,
    "shares_for_advertising": 5,
    "sells_user_data": 7,

    # data_sharing (medium-high)
    "shares_with_third_parties": 5,
    "shares_with_data_brokers": 8,
    "shares_with_government": 7,
    "shares_health_data": 9,
    "sells_sensitive_data": 10,

    # sensitive_data (high)
    "collects_precise_location": 8,
    "collects_health_information": 9,
    "collects_biometrics": 10,
    "collects_children_data": 10,

    # user_rights (high because user can’t protect themselves)
    "denies_user_access": 7,
    "no_access_correction_rights": 6,
    "no_data_portability": 6,
    "no_data_deletion": 9,

    # legal (medium-high)
    "unilateral_terms_change": 6,
    "waives_rights": 8,
    "class_action_waiver": 7,
    "binding_arbitration": 7,
    "indefinite_data_retention": 8,

    # extreme_cases (fun but max)
    "reidentifies_anonymous_data": 10,
    "forced_disclosure_of_data": 10,
    "life_control_technology": 10
}
