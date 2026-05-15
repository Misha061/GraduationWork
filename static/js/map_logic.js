function renderHistoryList(historyData) {
    console.log("LOG: Rendering history list...", historyData);
    var container = document.getElementById('historyList');
    if (!container) return;

    container.innerHTML = '';

    if (!historyData || !Array.isArray(historyData) || historyData.length === 0) {
        console.warn("LOG: History data is empty or invalid");
        container.innerHTML = '<div style="text-align: center; color: #888; padding: 15px;">Немає даних за останні 7 днів</div>';
        return;
    }

    var dataToRender = [...historyData].reverse();

    dataToRender.forEach(item => {
        var row = document.createElement('div');
        row.style = "display:flex; justify-content:space-between; padding:12px 15px; background:#f9f9f9; border-radius:6px; border:1px solid #e0e0e0; margin-bottom:5px; font-size:14px;";

        row.innerHTML = `
            <span style="font-weight: bold; color: #333;">
                <i class="fa-regular fa-clock" style="color: #1976d2;"></i> ${item.time}
            </span>
            <span>PM2.5: <strong style="color: #d32f2f;">${item.pm25}</strong></span>
            <span>PM10: <strong style="color: #f57c00;">${item.pm10}</strong></span>
        `;
        container.appendChild(row);
    });
    console.log("LOG: History list updated");
}

if (document.getElementById('map')) {
    console.log("LOG: Initializing map...");
    var mapElement = document.getElementById('map');

    if (mapElement._leaflet_id) {
        console.log("LOG: Cleaning up old map instance");
        mapElement._leaflet_id = null;
        mapElement.innerHTML = "";
    }

    var map = L.map('map').setView([48.3794, 31.1656], 6);

    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
        iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
    });

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    var markersLayer = L.layerGroup().addTo(map);
    var citySelector = document.getElementById('citySelector');
    var timeSelector = document.getElementById('timeSelector');

    function fetchDashboardData() {
        var cityId = citySelector.value;
        var timeVal = timeSelector ? timeSelector.value : 'now';

        console.log(`LOG: Starting fetch. City: ${cityId}, Hour: ${timeVal}`);

        if (cityId === 'none') {
            document.getElementById('statsCard').style.display = 'none';
            markersLayer.clearLayers();
            return;
        }

        var opt = citySelector.options[citySelector.selectedIndex];
        var lat = parseFloat(String(opt.getAttribute('data-lat')).replace(',', '.'));
        var lon = parseFloat(String(opt.getAttribute('data-lon')).replace(',', '.'));

        console.log(`LOG: Flying to city center: ${lat}, ${lon}`);
        map.flyTo([lat, lon], 12);

        fetch(`/api/get_air_status/${cityId}/?hour=${timeVal}`)
            .then(response => {
                console.log("LOG: Network response received");
                return response.json();
            })
            .then(data => {
                console.log("LOG: JSON data parsed:", data);

                document.getElementById('statsCard').style.display = 'block';
                document.getElementById('cityName').innerText = opt.text;
                document.getElementById('pm25_val').innerText = data.current_avg_pm25 || "0";
                document.getElementById('pm10_val').innerText = data.current_avg_pm10 || "0";

                var forecastSpan = document.getElementById('forecast');
                if (forecastSpan) {
                    forecastSpan.innerText = data.forecast_1h || "Немає даних";
                }

                markersLayer.clearLayers();

                if (data.locations && data.locations.length > 0) {
                    console.log(`LOG: Adding ${data.locations.length} markers to map`);
                    data.locations.forEach((loc, index) => {
                        var mLat = parseFloat(String(loc.lat).replace(',', '.'));
                        var mLon = parseFloat(String(loc.lon).replace(',', '.'));

                        if (!isNaN(mLat) && !isNaN(mLon)) {
                            L.marker([mLat, mLon]).addTo(markersLayer)
    .bindPopup(`
        <div style="text-align: center;">
            <b style="color: #2c3e50; font-size: 14px;">${loc.location_name}</b><br>
            <hr style="margin: 5px 0;">
            <span style="color: #e74c3c;">PM2.5: <b>${loc.pm25}</b></span><br>
            <span style="color: #f39c12;">PM10: <b>${loc.pm10}</b></span>
        </div>
    `);
                        } else {
                            console.error(`LOG: Failed to parse coordinates for point ${index}`);
                        }
                    });
                } else {
                    console.warn("LOG: No marker locations found in API response");
                }

                renderHistoryList(data.history_list);
            })
            .catch(err => {
                console.error("LOG: Critical error during fetch:", err);
            });
    }

    citySelector.addEventListener('change', () => {
        console.log("LOG: User changed city");
        fetchDashboardData();
    });

    if (timeSelector) {
        timeSelector.addEventListener('change', () => {
            console.log("LOG: User changed time");
            fetchDashboardData();
        });
    }

    if (citySelector.value !== 'none') {
        console.log("LOG: Initial load for selected city");
        fetchDashboardData();
    }
}