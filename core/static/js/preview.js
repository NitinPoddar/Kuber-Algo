function renderPython(conditions, indent = 1, connector = 'AND') {
  const pad = '  '.repeat(indent);
  let code = '';

  conditions.forEach((cond, i) => {
    const lhsParams = Object.entries(cond.lhs?.parameters || {})
      .map(([k, v]) => `${k}='${v}'`).join(', ');
    const lhsStr = cond.lhs?.name ? `${cond.lhs.name}(${lhsParams})` : '/* missing_lhs */';

    let rhsStr = '';
    if (cond.rhs?.type === 'value') {
      rhsStr = cond.rhs.value;
    } else if (cond.rhs?.type === 'variable') {
      const rhsParams = Object.entries(cond.rhs.parameters || {})
        .map(([k, v]) => `${k}='${v}'`).join(', ');
      rhsStr = `${cond.rhs.name}(${rhsParams})`;
    } else {
      rhsStr = '/* missing_rhs */';
    }

    const lineConnector = (i > 0) ? ` ${connector} ` : '';
    code += `${pad}${i > 0 ? lineConnector : ''}if ${lhsStr} ${cond.operator} ${rhsStr}:\n`;

    if (cond.children && cond.children.length > 0) {
      // default to nested AND unless you carry connector in your JSON
      code += renderPython(cond.children, indent + 1, cond.connector || 'AND');
    } else {
      code += `${'  '.repeat(indent + 1)}# action\n`;
    }
  });

  return code;
}



function showPreview() {
  const legBlocks = document.querySelectorAll('.leg-block'); // ✅ DOM
  const jsonPreview = document.getElementById('jsonPreview');
  const pythonPreview = document.getElementById('pythonPreview');
  const previewBox = document.getElementById('jsonPreviewBox');
  const results = [];
  let python = '';

legBlocks.forEach((leg, idx) => {
    const entry = extractConditions(document.getElementById(`entry_conditions_${idx}`));
    const exit = extractConditions(document.getElementById(`exit_conditions_${idx}`));
    results.push({ leg: idx + 1, entry_conditions: entry, exit_conditions: exit });
    python += `// Leg ${idx + 1} Entry\n`;
    python += renderPython(entry, 1);
    python += `\n// Leg ${idx + 1} Exit\n`;
    python += renderPython(exit, 1);
    python += '\n';
  });

  jsonPreview.textContent = JSON.stringify(results, null, 2);
  pythonPreview.textContent = python;
  previewBox.style.display = 'block';
}
const form = document.getElementById("algoForm");
form.addEventListener("submit", function(e) {
  const legBlocks = document.querySelectorAll('.leg-block'); // ✅ DOM
  legBlocks.forEach((leg, idx) => {
    const entry = extractConditions(document.getElementById(`entry_conditions_${idx}`));
    const exit = extractConditions(document.getElementById(`exit_conditions_${idx}`));
    const entryInput = document.createElement('input');
    entryInput.type = 'hidden';
    entryInput.name = `entry_conditions_json_${idx}`;
    entryInput.value = JSON.stringify(entry);
    form.appendChild(entryInput);
    const exitInput = document.createElement('input');
    exitInput.type = 'hidden';
    exitInput.name = `exit_conditions_json_${idx}`;
    exitInput.value = JSON.stringify(exit);
    form.appendChild(exitInput);
  });
});
$(function () {
  $(document).on('mouseenter', '.constant-builder', function () {
    $(this).sortable({
      axis: 'x',
      items: '> .constant-item',
      handle: '.handle',
      placeholder: 'drag-placeholder',
      tolerance: 'pointer'
    });
  });
});
