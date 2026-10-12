// Home page quote rotator. The quotes come from data/quotes.yaml, inlined in the page
// as JSON. It shows them in random order with no repeats until every quote has been
// shown, and changes the quote every 20 seconds. Rotation pauses while the tab is
// hidden and when the visitor prefers reduced motion. Without JavaScript the page
// keeps the quote it was built with.

const INTERVAL_MS = 20 * 1000;

const target = document.getElementById("quote");
const source = document.getElementById("quotes");

if (target && source) {
	const quotes = JSON.parse(source.textContent);
	const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
	let deck = [];
	let last = -1;
	let timer = null;

	// A shuffled list of every quote's index, never starting with the one just shown.
	const shuffle = () => {
		const order = quotes.map((_, i) => i);
		for (let i = order.length - 1; i > 0; i--) {
			const j = Math.floor(Math.random() * (i + 1));
			[order[i], order[j]] = [order[j], order[i]];
		}
		if (order.length > 1 && order[order.length - 1] === last) {
			[order[0], order[order.length - 1]] = [order[order.length - 1], order[0]];
		}
		return order;
	};

	const show = () => {
		if (deck.length === 0) {
			deck = shuffle();
		}
		last = deck.pop();
		const { text, source } = quotes[last];
		target.textContent = `"${text}" -- ${source}`;
	};

	const schedule = () => {
		clearInterval(timer);
		timer = null;
		if (!document.hidden && !reducedMotion.matches) {
			timer = setInterval(show, INTERVAL_MS);
		}
	};

	show();
	schedule();
	document.addEventListener("visibilitychange", schedule);
	reducedMotion.addEventListener("change", schedule);
}
