
USE food_donation_db;

-- 1. Show all currently available donations
SELECT
    d.id,
    d.food_name,
    d.quantity,
    d.unit,
    d.expiry_date,
    u.name AS donor_name
FROM donations AS d
JOIN users AS u ON d.donor_id = u.id
WHERE d.status = 'Available'
  AND d.expiry_date >= CURDATE()
ORDER BY d.expiry_date ASC;


-- 2. Count donations by status
SELECT
    status,
    COUNT(*) AS total
FROM donations
GROUP BY status;


-- 3. Find NGOs and their request counts
SELECT
    u.name AS ngo_name,
    COUNT(r.id) AS total_requests
FROM users AS u
LEFT JOIN requests AS r ON r.ngo_id = u.id
WHERE u.role = 'ngo'
GROUP BY u.id, u.name
ORDER BY total_requests DESC;


-- 4. Find food items requested by NGOs
SELECT
    d.food_name,
    SUM(r.quantity_requested) AS quantity_requested
FROM requests AS r
JOIN donations AS d ON d.id = r.donation_id
GROUP BY d.id, d.food_name
ORDER BY quantity_requested DESC;


-- 5. Show request counts by status
SELECT
    status,
    COUNT(*) AS total_requests
FROM requests
GROUP BY status;


-- 6. Show total distributed quantity by food item
SELECT
    d.food_name,
    d.unit,
    SUM(ds.distributed_quantity) AS total_distributed
FROM distributions AS ds
JOIN requests AS r ON r.id = ds.request_id
JOIN donations AS d ON d.id = r.donation_id
GROUP BY d.food_name, d.unit
ORDER BY total_distributed DESC;


-- 7. Find NGOs with no requests
SELECT
    u.id,
    u.name,
    u.email
FROM users AS u
LEFT JOIN requests AS r ON r.ngo_id = u.id
WHERE u.role = 'ngo'
  AND r.id IS NULL;


-- 8. Show requests with NGO, food and status
SELECT
    r.id AS request_id,
    u.name AS ngo_name,
    d.food_name,
    r.quantity_requested,
    d.unit,
    r.status
FROM requests AS r
JOIN users AS u ON u.id = r.ngo_id
JOIN donations AS d ON d.id = r.donation_id
ORDER BY r.id DESC;
