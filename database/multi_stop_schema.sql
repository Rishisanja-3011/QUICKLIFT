ALTER TABLE rides
    ADD COLUMN route_geojson MEDIUMTEXT NULL,
    ADD COLUMN duration_minutes INT NULL;

CREATE TABLE IF NOT EXISTS ride_stops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ride_id INT NOT NULL,
    stop_name VARCHAR(255) NOT NULL,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    distance_from_start FLOAT NOT NULL DEFAULT 0,
    stop_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ride_order (ride_id, stop_order),
    INDEX idx_stop_name (stop_name),
    CONSTRAINT fk_ride_stops_ride
        FOREIGN KEY (ride_id) REFERENCES rides(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS geocode_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cache_key VARCHAR(64) NOT NULL UNIQUE,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    place_name VARCHAR(255),
    provider VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE bookings
    ADD COLUMN pickup_stop_id INT NULL,
    ADD COLUMN drop_stop_id INT NULL,
    ADD COLUMN pickup_name VARCHAR(255) NULL,
    ADD COLUMN drop_name VARCHAR(255) NULL,
    ADD COLUMN segment_distance_km DECIMAL(10,2) NULL,
    ADD COLUMN booked_price DECIMAL(10,2) NULL;
