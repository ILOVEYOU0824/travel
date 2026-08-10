const form = document.querySelector("#tripForm");
const statusBox = document.querySelector("#status");
const submitButton = document.querySelector("#submitButton");
const resultTitle = document.querySelector("#resultTitle");
const nightsBadge = document.querySelector("#nightsBadge");
const planText = document.querySelector("#planText");
const lodgingList = document.querySelector("#lodgingList");
const attractionList = document.querySelector("#attractionList");

const map = L.map("map", {
  zoomControl: false,
}).setView([35.6812, 139.7671], 12);

L.control.zoom({ position: "bottomright" }).addTo(map);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap",
}).addTo(map);

let markerLayer = L.layerGroup().addTo(map);
let routeLine = null;

setTimeout(() => map.invalidateSize(), 200);
window.addEventListener("resize", () => map.invalidateSize());

function money(value) {
  return new Intl.NumberFormat("ko-KR").format(value);
}

function setStatus(message, type = "info") {
  statusBox.textContent = message;
  statusBox.style.background = type === "error" ? "#fff0f0" : "#fff1f4";
  statusBox.style.color = type === "error" ? "#d3182f" : "#e51f46";
}

function markerIcon(kind, label) {
  return L.divIcon({
    className: "",
    html: `<div class="marker ${kind}">${label}</div>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -18],
  });
}

function itemCard(item, type) {
  const price = type === "lodging" ? `<span>${money(item.price_per_night)}원/박</span>` : "";
  return `
    <article class="mini-card">
      <strong>${item.name}</strong>
      <p>${item.area || "주소 정보 없음"}</p>
      <div class="meta">
        <span>평점 ${item.rating || "-"}</span>
        ${price}
        <span>${item.provider}</span>
      </div>
      <a href="${item.url}" target="_blank" rel="noreferrer">지도에서 보기</a>
    </article>
  `;
}

function renderCards(data) {
  lodgingList.innerHTML = data.lodgings.slice(0, 5).map((item) => itemCard(item, "lodging")).join("");
  attractionList.innerHTML = data.attractions.slice(0, 8).map((item) => itemCard(item, "place")).join("");
}

function renderMap(data) {
  markerLayer.clearLayers();
  if (routeLine) {
    map.removeLayer(routeLine);
    routeLine = null;
  }

  const points = [];
  const bestHotel = data.lodgings.find((item) => item.lat && item.lng);

  if (bestHotel) {
    const point = [bestHotel.lat, bestHotel.lng];
    points.push(point);
    L.marker(point, { icon: markerIcon("hotel", "H") })
      .bindPopup(`<b>${bestHotel.name}</b><br>${money(bestHotel.price_per_night)}원/박`)
      .addTo(markerLayer);
  }

  data.attractions
    .filter((item) => item.lat && item.lng)
    .slice(0, 8)
    .forEach((item, index) => {
      const point = [item.lat, item.lng];
      points.push(point);
      L.marker(point, { icon: markerIcon("place", index + 1) })
        .bindPopup(`<b>${index + 1}. ${item.name}</b><br>평점 ${item.rating || "-"}`)
        .addTo(markerLayer);
    });

  if (points.length > 1) {
    routeLine = L.polyline(points, {
      color: "#ff3358",
      weight: 5,
      opacity: 0.78,
      dashArray: "10, 10",
    }).addTo(map);
  }

  if (points.length) {
    map.fitBounds(L.latLngBounds(points), { padding: [80, 80] });
  }
}

async function createPlan(payload) {
  const response = await fetch("/api/trips/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "일정을 만들지 못했습니다.");
  }

  return response.json();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  submitButton.textContent = "AI가 코스를 만드는 중...";
  setStatus("호텔과 관광지를 찾고 AI 일정으로 정리하고 있습니다.");

  const payload = {
    destination: document.querySelector("#destination").value.trim(),
    start_date: document.querySelector("#startDate").value,
    end_date: document.querySelector("#endDate").value,
    people: Number(document.querySelector("#people").value),
    budget: Number(document.querySelector("#budget").value),
  };

  try {
    const data = await createPlan(payload);
    resultTitle.textContent = `${data.destination} 추천 여행`;
    nightsBadge.textContent = `${data.nights}박 ${data.nights + 1}일`;
    planText.textContent = data.plan;
    renderCards(data);
    renderMap(data);
    setStatus(`완료: 숙소 ${data.lodgings.length}개, 관광지 ${data.attractions.length}개를 반영했습니다.`);
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "추천 코스 만들기";
  }
});
