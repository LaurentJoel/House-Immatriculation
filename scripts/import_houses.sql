-- Create staging table with 70 generic text columns to receive the COPY data
DROP TABLE IF EXISTS public.houses_immat;
CREATE TABLE public.houses_immat (
    col0 TEXT, col1 TEXT, col2 TEXT, col3 TEXT, col4 TEXT,
    col5 TEXT, col6 TEXT, col7 TEXT, col8 TEXT, col9 TEXT,
    col10 TEXT, col11 TEXT, col12 TEXT, col13 TEXT, col14 TEXT,
    col15 TEXT, col16 TEXT, col17 TEXT, col18 TEXT, col19 TEXT,
    col20 TEXT, col21 TEXT, col22 TEXT, col23 TEXT, col24 TEXT,
    col25 TEXT, col26 TEXT, col27 TEXT, col28 TEXT, col29 TEXT,
    col30 TEXT, col31 TEXT, col32 TEXT, col33 TEXT, col34 TEXT,
    col35 TEXT, col36 TEXT, col37 TEXT, col38 TEXT, col39 TEXT,
    col40 TEXT, col41 TEXT, col42 TEXT, col43 TEXT, col44 TEXT,
    col45 TEXT, col46 TEXT, col47 TEXT, col48 TEXT, col49 TEXT,
    col50 TEXT, col51 TEXT, col52 TEXT, col53 TEXT, col54 TEXT,
    col55 TEXT, col56 TEXT, col57 TEXT, col58 TEXT, col59 TEXT,
    col60 TEXT, col61 TEXT, col62 TEXT, col63 TEXT, col64 TEXT,
    col65 TEXT, col66 TEXT, col67 TEXT, col68 TEXT, col69 TEXT
);

-- Import the raw COPY data
\copy public.houses_immat FROM '/tmp/bck_houses_immat'

-- Verify the count
SELECT COUNT(*) AS total_houses FROM public.houses_immat;

-- Check how many have immatriculation numbers (col69)
SELECT COUNT(*) AS houses_with_immat FROM public.houses_immat WHERE col69 IS NOT NULL AND col69 != '';
