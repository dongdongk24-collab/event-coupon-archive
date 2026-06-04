const today = new Date();
today.setHours(0, 0, 0, 0);

const normalize = (value) => value.toString().trim().toLowerCase().replace(/\s+/g, " ");
const daysUntil = (dateText) => {
  if (!dateText) return Number.POSITIVE_INFINITY;
  const date = new Date(`${dateText}T00:00:00`);
  return Math.ceil((date - today) / 86400000);
};

function statusFor(event) {
  const left = daysUntil(event.endDate);
  if (left < 0) return "closed";
  if (left <= 3) return "closing";
  return "open";
}

function statusLabel(status) {
  return { open: "진행 중", closing: "마감 임박", closed: "마감" }[status] || status;
}

function eventTemplate(event) {
  const status = statusFor(event);
  const reward = event.reward || "경품 정보 확인 필요";
  const organizer = event.organizer || "주최 확인 필요";

  return `
    <article class="event-card">
      <div class="event-top">
        <span class="badge ${status}">${statusLabel(status)}</span>
        <span class="badge">${event.category}</span>
        <span class="badge">${reward}</span>
      </div>
      <h3>${event.title}</h3>
      <div class="event-meta">
        <span>주최: ${organizer}</span>
        <span>마감: ${event.endDate || "확인 필요"}</span>
        <span>발표: ${event.announcementDate || "확인 필요"}</span>
      </div>
      <p class="event-summary">${event.summary}</p>
      <div class="event-meta">
        <span>참여: ${event.method}</span>
        <span>주의: ${event.caution}</span>
      </div>
      <div class="event-actions">
        <a class="primary" href="${event.url}">이벤트 보기</a>
        <a href="${event.sourceUrl}">출처 확인</a>
      </div>
    </article>
  `;
}

async function init() {
  const list = document.querySelector("[data-event-list]");
  const count = document.querySelector("[data-result-count]");
  const search = document.querySelector("[data-search]");
  const category = document.querySelector("[data-category]");
  const status = document.querySelector("[data-status]");
  const quickButtons = document.querySelectorAll("[data-quick]");

  let events = [];
  try {
    const response = await fetch("data/events.json", { cache: "no-store" });
    events = await response.json();
  } catch (error) {
    list.innerHTML = `<p class="empty">이벤트 데이터를 불러오지 못했습니다.</p>`;
    return;
  }

  const render = () => {
    const query = normalize(search.value);
    const selectedCategory = category.value;
    const selectedStatus = status.value;

    const matches = events.filter((event) => {
      const eventStatus = statusFor(event);
      const haystack = normalize([
        event.title,
        event.organizer,
        event.category,
        event.reward,
        event.summary,
        event.method,
        event.caution,
        ...(event.tags || [])
      ].join(" "));

      const queryMatch = !query || query.split(" ").every((term) => haystack.includes(term));
      const categoryMatch = selectedCategory === "all" || event.category === selectedCategory || (event.tags || []).includes(selectedCategory);
      const statusMatch = selectedStatus === "all" || eventStatus === selectedStatus || (selectedStatus === "open" && eventStatus !== "closed");
      return queryMatch && categoryMatch && statusMatch;
    }).sort((a, b) => daysUntil(a.endDate) - daysUntil(b.endDate));

    count.textContent = `${matches.length}건의 이벤트를 찾았습니다.`;
    list.innerHTML = matches.length ? matches.map(eventTemplate).join("") : `<p class="empty">조건에 맞는 이벤트가 없습니다.</p>`;
  };

  search.addEventListener("input", render);
  category.addEventListener("change", render);
  status.addEventListener("change", render);
  quickButtons.forEach((button) => {
    button.addEventListener("click", () => {
      search.value = button.dataset.quick;
      render();
    });
  });

  render();
}

init();
