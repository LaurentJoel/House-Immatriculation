-- ============================================
-- DGI Cameroun - Tax Summary Tables Setup
-- Pre-computes tax estimates at each admin level
-- ============================================

-- Tax Calculation Formula:
-- Annual Tax = area_m2 × prix_m2_fcfa × redevance_rate
-- Example: 100 m² in Yaoundé = 100 × 10000 × 0.25 = 250,000 FCFA/year

-- ── Step 1: Create mercuriale lookup by commune name ─────────────
DROP TABLE IF EXISTS immatriculation.mercuriale_lookup;
CREATE TABLE immatriculation.mercuriale_lookup AS
SELECT 
    m.arrondissement as commune_name,
    m.departement,
    m.region,
    m.prix_m2_fcfa,
    m.redevance_residentiel,
    m.mult_commercial,
    m.redevance_commercial
FROM immatriculation.mercuriale_prix m;

CREATE INDEX idx_merc_lookup_commune ON immatriculation.mercuriale_lookup(commune_name);

-- ── Step 2: Link communes to mercuriale prices ───────────────────
DROP TABLE IF EXISTS immatriculation.commune_prices;
CREATE TABLE immatriculation.commune_prices AS
SELECT 
    a.gid as commune_gid,
    a.adm3_name as commune_name,
    a.adm2_name as dept_name,
    a.adm1_name as region_name,
    a.adm3_pcode as pcode,
    a.area_sqkm,
    COALESCE(m.prix_m2_fcfa, 500) as prix_m2_fcfa,  -- Default 500 for unmatched
    COALESCE(m.redevance_residentiel, 0.25) as redevance_rate,
    COALESCE(m.mult_commercial, 2.0) as mult_commercial
FROM public.cmr_admin3 a
LEFT JOIN immatriculation.mercuriale_lookup m 
    ON LOWER(TRIM(a.adm3_name)) = LOWER(TRIM(m.commune_name))
    OR LOWER(TRIM(SPLIT_PART(a.adm3_name, ' ', 1))) = LOWER(TRIM(m.commune_name));

CREATE INDEX idx_cp_gid ON immatriculation.commune_prices(commune_gid);

-- ── Step 3: Create summary at COMMUNE level ──────────────────────
DROP TABLE IF EXISTS immatriculation.tax_summary_communes;
CREATE TABLE immatriculation.tax_summary_communes AS
SELECT 
    cp.commune_gid as gid,
    cp.commune_name as name,
    cp.dept_name,
    cp.region_name,
    cp.pcode,
    cp.prix_m2_fcfa,
    COUNT(h.col0) as nb_batiments,
    ROUND(SUM(CAST(h.col67 AS NUMERIC))::numeric, 2) as surface_totale_m2,
    -- Tax estimate: area × prix × redevance rate
    ROUND((SUM(CAST(h.col67 AS NUMERIC)) * cp.prix_m2_fcfa * cp.redevance_rate)::numeric, 0) as impot_estime_fcfa,
    -- Airbnb counts
    (SELECT COUNT(*) FROM immatriculation.airbnb_listings ab 
     WHERE ab.matched_commune ILIKE '%' || cp.commune_name || '%') as nb_airbnb,
    (SELECT COUNT(*) FROM immatriculation.airbnb_listings ab 
     WHERE ab.matched_commune ILIKE '%' || cp.commune_name || '%' AND ab.matched_immat IS NOT NULL) as nb_airbnb_matched
FROM immatriculation.commune_prices cp
LEFT JOIN public.houses_immat h ON h.commune_gid = cp.commune_gid
GROUP BY cp.commune_gid, cp.commune_name, cp.dept_name, cp.region_name, cp.pcode, cp.prix_m2_fcfa, cp.redevance_rate;

CREATE INDEX idx_tsc_gid ON immatriculation.tax_summary_communes(gid);
CREATE INDEX idx_tsc_dept ON immatriculation.tax_summary_communes(dept_name);
CREATE INDEX idx_tsc_region ON immatriculation.tax_summary_communes(region_name);

-- ── Step 4: Create summary at DEPARTMENT level ───────────────────
DROP TABLE IF EXISTS immatriculation.tax_summary_departments;
CREATE TABLE immatriculation.tax_summary_departments AS
SELECT 
    d.gid,
    d.name,
    d.name_en,
    (SELECT r.name FROM immatriculation.admin_regions r 
     WHERE ST_Contains(r.geom, ST_Centroid(d.geom)) LIMIT 1) as region_name,
    SUM(c.nb_batiments) as nb_batiments,
    SUM(c.surface_totale_m2) as surface_totale_m2,
    SUM(c.impot_estime_fcfa) as impot_estime_fcfa,
    ROUND(AVG(c.prix_m2_fcfa)::numeric, 0) as prix_mercurial_moyen,
    SUM(c.nb_airbnb) as nb_airbnb,
    SUM(c.nb_airbnb_matched) as nb_airbnb_matched
FROM immatriculation.admin_departments d
LEFT JOIN immatriculation.tax_summary_communes c 
    ON ST_Contains(d.geom, 
        (SELECT ST_Centroid(geom) FROM public.cmr_admin3 WHERE gid = c.gid LIMIT 1))
GROUP BY d.gid, d.name, d.name_en, d.geom;

CREATE INDEX idx_tsd_gid ON immatriculation.tax_summary_departments(gid);
CREATE INDEX idx_tsd_region ON immatriculation.tax_summary_departments(region_name);

-- ── Step 5: Create summary at REGION level ───────────────────────
DROP TABLE IF EXISTS immatriculation.tax_summary_regions;
CREATE TABLE immatriculation.tax_summary_regions AS
SELECT 
    r.gid,
    r.name,
    r.name_en,
    COALESCE(SUM(d.nb_batiments), 0) as nb_batiments,
    COALESCE(SUM(d.surface_totale_m2), 0) as surface_totale_m2,
    COALESCE(SUM(d.impot_estime_fcfa), 0) as impot_estime_fcfa,
    COALESCE(ROUND(AVG(d.prix_mercurial_moyen)::numeric, 0), 0) as prix_mercurial_moyen,
    COALESCE(SUM(d.nb_airbnb), 0) as nb_airbnb,
    COALESCE(SUM(d.nb_airbnb_matched), 0) as nb_airbnb_matched
FROM immatriculation.admin_regions r
LEFT JOIN immatriculation.tax_summary_departments d ON d.region_name = r.name
GROUP BY r.gid, r.name, r.name_en;

CREATE INDEX idx_tsr_gid ON immatriculation.tax_summary_regions(gid);

-- ── Step 6: Create national totals ───────────────────────────────
DROP TABLE IF EXISTS immatriculation.tax_summary_national;
CREATE TABLE immatriculation.tax_summary_national AS
SELECT 
    'Cameroun' as name,
    SUM(nb_batiments) as total_batiments,
    SUM(surface_totale_m2) as total_surface_m2,
    SUM(impot_estime_fcfa) as total_impot_estime_fcfa,
    SUM(nb_airbnb) as airbnb_total,
    SUM(nb_airbnb_matched) as airbnb_matched
FROM immatriculation.tax_summary_regions;

-- ── Step 7: Add building tax column to houses ────────────────────
-- This pre-computes individual building taxes
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'houses_immat' AND column_name = 'impot_annuel') THEN
        ALTER TABLE public.houses_immat ADD COLUMN impot_annuel NUMERIC(12,2);
    END IF;
END $$;

-- Update building taxes (this may take a while for 3.8M rows)
UPDATE public.houses_immat h
SET impot_annuel = ROUND(
    CAST(h.col67 AS NUMERIC) * 
    COALESCE(cp.prix_m2_fcfa, 500) * 
    COALESCE(cp.redevance_rate, 0.25), 2
)
FROM immatriculation.commune_prices cp
WHERE h.commune_gid = cp.commune_gid;

-- ── Final: Show summary statistics ───────────────────────────────
SELECT 'National Summary' as level, name, total_batiments, 
       total_impot_estime_fcfa / 1000000000.0 as impot_milliards_fcfa,
       airbnb_total
FROM immatriculation.tax_summary_national;

SELECT 'Regional Summary' as level, name, nb_batiments, 
       impot_estime_fcfa / 1000000000.0 as impot_milliards_fcfa,
       nb_airbnb
FROM immatriculation.tax_summary_regions 
ORDER BY impot_estime_fcfa DESC;
