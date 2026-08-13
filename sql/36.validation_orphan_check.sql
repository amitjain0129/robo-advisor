SELECT p.persona_id, p.label, p.final_tier_name,
       COUNT(w.ticker) AS n_weight_rows
FROM dim_user_profile p
LEFT JOIN fact_tier_weights w
  ON p.final_tier_name = w.tier_name
GROUP BY p.persona_id, p.label, p.final_tier_name
ORDER BY p.persona_id