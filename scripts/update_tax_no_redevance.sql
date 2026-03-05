-- ============================================
-- Update: Remove redevance rate from tax calculation
-- New formula: Valeur Foncière = Surface × Prix_m2
-- ============================================

-- Update commune_prices to set redevance to 1.0 (no multiplication)
UPDATE immatriculation.commune_prices SET redevance_rate = 1.0;

-- Recalculate commune-level summaries
UPDATE immatriculation.tax_summary_communes tc
SET impot_estime_fcfa = ROUND(surface_totale_m2 * prix_m2_fcfa, 0)
WHERE surface_totale_m2 IS NOT NULL;

-- Recalculate department-level summaries
UPDATE immatriculation.tax_summary_departments d
SET impot_estime_fcfa = (
    SELECT SUM(c.impot_estime_fcfa)
    FROM immatriculation.tax_summary_communes c
    WHERE ST_Contains(
        (SELECT geom FROM immatriculation.admin_departments WHERE gid = d.gid),
        (SELECT ST_Centroid(geom) FROM public.cmr_admin3 WHERE gid = c.gid LIMIT 1)
    )
);

-- Recalculate region-level summaries
UPDATE immatriculation.tax_summary_regions r
SET impot_estime_fcfa = (
    SELECT COALESCE(SUM(d.impot_estime_fcfa), 0)
    FROM immatriculation.tax_summary_departments d
    WHERE d.region_name = r.name
);

-- Recalculate national total
UPDATE immatriculation.tax_summary_national
SET total_impot_estime_fcfa = (
    SELECT SUM(impot_estime_fcfa) FROM immatriculation.tax_summary_regions
);

-- Show results
SELECT 'Updated Tax Summary (no redevance)' as info;
SELECT name, nb_batiments, 
       TO_CHAR(impot_estime_fcfa, 'FM999,999,999,999,999') as valeur_fonciere_fcfa
FROM immatriculation.tax_summary_regions 
ORDER BY impot_estime_fcfa DESC;
