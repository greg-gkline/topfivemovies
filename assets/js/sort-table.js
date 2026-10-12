// Sortable index tables. Each <th data-sort="text|number"> becomes a button that
// sorts the table's rows by that column, in the order given by data-sort-dir
// (asc by default), and restripes the rows. Without JavaScript the table stays in
// its built order, newest first. A cell's data-sort-value, if any, is sorted on
// instead of its text.

const collator = new Intl.Collator("en", { sensitivity: "base", numeric: true });

const cellValue = (row, column) => {
	const cell = row.cells[column];
	return cell.dataset.sortValue ?? cell.textContent.trim();
};

for (const table of document.querySelectorAll("table[data-sortable]")) {
	const body = table.tBodies[0];
	for (const th of table.querySelectorAll("th[data-sort]")) {
		const button = document.createElement("button");
		button.type = "button";
		button.append(...th.childNodes);
		th.append(button);

		button.addEventListener("click", () => {
			const column = th.cellIndex;
			const numeric = th.dataset.sort === "number";
			const sign = th.dataset.sortDir === "desc" ? -1 : 1;
			const rows = [...body.rows];
			rows.sort((a, b) => {
				const x = cellValue(a, column);
				const y = cellValue(b, column);
				return sign * (numeric ? Number(x) - Number(y) : collator.compare(x, y));
			});
			rows.forEach((row, i) => {
				row.classList.toggle("even", i % 2 === 0);
				row.classList.toggle("odd", i % 2 === 1);
				body.append(row);
			});
			for (const other of table.querySelectorAll("th[aria-sort]")) {
				other.removeAttribute("aria-sort");
			}
			th.setAttribute("aria-sort", sign < 0 ? "descending" : "ascending");
		});
	}
}
