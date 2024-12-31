
class BasestationMap {
    static STYLE_REGION = { color: 'black', fillOpacity: 0};
    static STYLE_INNER_RING = {
        radius: 10000,
        color: 'blue',
        stroke: true,
        opacity: 0.25,
        fillColor: '#00f',
        fillOpacity: 0.0
    };
    static STYLE_OUTER_RING = {
        radius: 20000,
        stroke: false,
        fillOpacity: 0.15
    };
    static STYLE_POINT = {
        radius: 1000,
        color: 'black',
        stroke: false,
        fillColor: '#fff',
        fillOpacity: 1.0
    };

    static CASTER_COLOR = {
        RTK2GO: 'blue',
        CENTIPEDE: 'purple',
        EMLID: 'red'
    }


    constructor(region_path, stations_path, lat = 64.5, lon = 26, zoom = 10, padding = 50) {
        this.region_path = region_path;
        this.stations_path = stations_path;
        this.lat = lat;
        this.lon = lon;
        this.zoom = zoom;
        this.padding = padding;
        this.map = L.map('map', { zoomControl: false }).setView([lat, lon], zoom);
        this.tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(this.map);
        //this.map.on('zoomend', this.zoomed_event(this.map));    
    }

    geoJSONtoSVGPath(geoJSON) {
        var coords = geoJSON.features[0].geometry.coordinates[0];
        var path = 'M' + coords.map(coord => coord.join(',')).join('L') + 'Z';
        return path;
    }

    async fetchRegionBorder() {
        if (this.region_path === null) {
            return;
        }

        let response = await fetch(this.region_path)
        let data = await response.json();

        let svgPath = this.geoJSONtoSVGPath(data);
        var svgElement = document.createElementNS("http://www.w3.org/2000/svg", "path");
        svgElement.setAttribute('d', svgPath);
        svgElement.setAttribute('stroke', 'red');
        svgElement.setAttribute('stroke-width', '10');
        svgElement.setAttribute('fill', 'none');
        svgElement.setAttribute('stroke-dasharray', '10000'); // Large number to start; adjust based on path length
        svgElement.setAttribute('stroke-dashoffset', '10000'); // Start with full offset to hide the line

        var svgLayer = L.svgOverlay(svgElement, this.map.getBounds());
        svgLayer.addTo(this.map);

        svgElement.style.animation = 'draw 10s linear forwards';

        let geojson_layer = L.geoJSON(data, BasestationMap.STYLE_REGION)// .addTo(this.map);
        this.map.fitBounds(geojson_layer.getBounds(), {padding: [this.padding, this.padding]});

        // Create a huge polygon for the outer boundary
        var outerCoords = [[-180, -90], [-180, 90], [180, 90], [180, -90], [-180, -90]];
        // Combine outer and inner (GeoJSON) coordinates
        var maskGeometry = {
            "type": "Polygon",
            "coordinates": [outerCoords].concat(data.features[0].geometry.coordinates)
        };
        L.geoJSON(maskGeometry, {
            style: {
                fillColor: 'black',
                weight: 0,
                fillOpacity: 0.3
            }
        }).addTo(this.map);

    }

    async fetchAndDisplayStations() {
        let response = await fetch(this.stations_path)
        let data = await response.json();
        data.stations.forEach(location => {
            let latLng = L.latLng(location.lat, location.lon);

            // Add outer circle
            let style = BasestationMap.STYLE_OUTER_RING;
            style.fillColor = BasestationMap.CASTER_COLOR[location.caster];
            L.circle(latLng, style).addTo(this.map);

            // Add inner circle
            // L.circle(latLng, BasestationMap.STYLE_INNER_RING).addTo(this.map);
        });
        data.stations.forEach(location => {
            let latLng = L.latLng(location.lat, location.lon);

            // Add center point
            var point = L.circle(latLng, BasestationMap.STYLE_POINT).addTo(this.map);
            point.bindPopup(location.id);
        });
    }

    zoomed_event(src) {
        return function(evt) {
            console.log(evt);
            console.log(src.getZoom());    
        }
    };
}

window.onload = async() => {
    let bsmap = new BasestationMap(region_file, station_file);

    await bsmap.fetchRegionBorder();
    await bsmap.fetchAndDisplayStations();
}
