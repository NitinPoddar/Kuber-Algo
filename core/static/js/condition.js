// Put this near the top of condition.js
// condition.js (top-level helpers)

function getRowsContainer(hostOrId) {
  const host = (typeof hostOrId === 'string') ? document.getElementById(hostOrId) : hostOrId;
  if (!host) return null;

  // If we're already a .conditions container, use it
  if (host.classList && host.classList.contains('conditions')) return host;

  // If root wrapper exists, use it
  const existing = host.querySelector(':scope > .nested-condition > .conditions');
  if (existing) return existing;

  // Otherwise create a root wrapper (no rows yet)
  const id = `group_${Math.random().toString(36).slice(2, 8)}`;
  const div = document.createElement('div');
  div.className = 'nested-condition mt-2';
  div.innerHTML = `
    <div class="is-flex is-justify-content-space-between mb-2">
      <strong>Condition</strong>
      <button type="button" class="delete" onclick="removeRootCondition('${host.id}', this)"></button>
    </div>
    <div class="field">
      <label class="label">Connector</label>
      <div class="select">
        <select class="group-connector">
          <option value="AND">AND</option>
          <option value="OR">OR</option>
        </select>
      </div>
    </div>
    <div class="conditions" id="${id}"></div>
    <button type="button" class="button is-small is-link mt-2" onclick="addConditionRow('${id}')">➕ Add Condition</button>
  `;
  host.appendChild(div);
  return div.querySelector('.conditions');
}

function ensureGroup(containerId) {
  const host = document.getElementById(containerId);
  if (!host) return null;

  // If we're already inside a .conditions container, just use it
  if (host.classList.contains('conditions')) return host;

  // If a root group already exists, use its .conditions
  const existing = host.querySelector(':scope > .nested-condition > .conditions');
  if (existing) return existing;

  // Otherwise create a root group wrapper (NO rows yet)
  const id = `group_${Math.random().toString(36).slice(2, 8)}`;
  const div = document.createElement('div');
  div.className = 'nested-condition mt-2';
  div.innerHTML = `
    <div class="is-flex is-justify-content-space-between mb-2">
      <strong>Condition</strong>
      <button type="button" class="delete" onclick="removeRootCondition('${containerId}', this)"></button>
    </div>
    <div class="field">
      <label class="label">Connector</label>
      <div class="select">
        <select class="group-connector">
          <option value="AND">AND</option>
          <option value="OR">OR</option>
        </select>
      </div>
    </div>
    <div class="conditions" id="${id}"></div>
    <button type="button" class="button is-small is-link mt-2" onclick="addConditionRow('${id}')">➕ Add Condition</button>
  `;
  host.appendChild(div);
  return div.querySelector('.conditions');
}



function addLeg() {
  const container = document.getElementById("legsContainer");
  const legIndex = document.querySelectorAll(".leg-block").length;
  const instrumentSelectId = `instrument_select_${legIndex}_${Date.now()}`;
  const legDiv = document.createElement("div");
  legDiv.classList.add("box", "leg-block", "mt-5");

  legDiv.innerHTML = `
    <h2 class="subtitle">Leg ${legIndex + 1}</h2>
    <div class="field">
      <label class="label">Instrument</label>
      <div class="select is-fullwidth">
        <select id="${instrumentSelectId}" class="instrument-dropdown" name="instrument_name[]" onchange="populateExpiryAndStrike(this, ${legIndex})" required style="width: 100%;">
          <option value="">--Select--</option>
          ${instruments.map(i => `<option value="${i.name}">${i.name}</option>`).join("")}
        </select>
      </div>
    </div>
    <div class="field">
      <label class="label">Expiry</label>
      <div class="select">
        <select name="expiry_date[]" id="expiry_${legIndex}" required></select>
      </div>
    </div>
    <div class="field">
      <label class="label">Strike</label>
      <div class="select">
        <select name="strike_price[]" id="strike_${legIndex}" required></select>
      </div>
    </div>
    <div class="field">
      <label class="label">Option Type</label>
      <div class="select">
        <select name="option_type[]" required>
          <option value="CE">Call (CE)</option>
          <option value="PE">Put (PE)</option>
        </select>
      </div>
    </div>
    <div class="field">
      <label class="label">Order Direction</label>
      <div class="select">
        <select name="order_direction[]" required>
          <option value="BUY">Buy</option>
          <option value="SELL">Sell</option>
        </select>
      </div>
    </div>
    <div class="field">
      <label class="label">Order Type</label>
      <div class="select">
        <select name="order_type[]" required>
          <option value="MARKET">Market</option>
          <option value="LIMIT">Limit</option>
          <option value="LIMITTHENMARKET">LimitThenMarket</option>
        </select>
      </div>
    </div>
    <div class="field">
      <label class="label">Entry Conditions</label>
      <div id="entry_conditions_${legIndex}" class="condition-group"></div>
      <button type="button" class="button is-small is-link mt-2" onclick="addRootCondition('entry_conditions_${legIndex}', this)">➕ Condition</button>
    </div>

    <div class="field">
      <label class="label">Exit Conditions</label>
      <div id="exit_conditions_${legIndex}" class="condition-group"></div>
      <button type="button" class="button is-small is-link mt-2" onclick="addRootCondition('exit_conditions_${legIndex}', this)">➕ Condition</button>
    </div>
  `;

  container.appendChild(legDiv);

  // Activate Select2 on instrument dropdown
  setTimeout(() => {
    $(`#${instrumentSelectId}`).select2({
      width: '100%',
      placeholder: "Search symbol",
      allowClear: true
    });
  }, 0);
}

function populateExpiryAndStrike(selectEl, legIndex) {
  const selected = selectEl.value;
  const expirySelect = document.getElementById(`expiry_${legIndex}`);
  const strikeSelect = document.getElementById(`strike_${legIndex}`);
  const matches = instruments.filter(i => i.name === selected);

  let expiries = new Set();
  let strikes = new Set();

  matches.forEach(i => {
    (i.expiries || []).forEach(e => expiries.add(e));
    (i.strikes || []).forEach(s => strikes.add(s));
  });

  expirySelect.innerHTML = [...expiries].sort().map(e => `<option value="${e}">${e}</option>`).join('');
  strikeSelect.innerHTML = [...strikes].sort((a, b) => a - b).map(s => `<option value="${s}">${s}</option>`).join('');
}

function addConditionGroup(containerId) {
  const container = document.getElementById(containerId);
  const id = `group_${Math.random().toString(36).substring(2, 8)}`;
  const div = document.createElement("div");
  div.classList.add("box", "nested-condition", "mt-3");

  div.innerHTML = `
    <div class="is-flex is-justify-content-space-between mb-2">
      <strong>Condition Group</strong>
      <button type="button" class="delete" onclick="this.closest('.nested-condition').remove()"></button>
    </div>
    <div class="field">
      <label class="label">Connector</label>
      <div class="select">
        <select class="group-connector">
          <option value="AND">AND</option>
          <option value="OR">OR</option>
        </select>
      </div>
    </div>
    <div class="conditions" id="${id}"></div>
    <button type="button" class="button is-small is-link mt-2" onclick="addConditionRow(this)">➕ Add Condition</button>
  `;

  container.appendChild(div);
}

function addConditionRow(target) {
  // target can be an element or an id
  let container = (typeof target === 'string') ? document.getElementById(target) : target;
  if (!container) return;

  // Always resolve to a real ".conditions" container (creates root wrapper if needed)
  container = getRowsContainer(container);
  if (!container) return;

  const row = document.createElement('div');
  row.classList.add('condition-row', 'is-flex', 'is-align-items-center', 'mb-2');

  // --- build your row exactly as before (unchanged UI bits) ---
  // LHS
  const lhsWrapper = document.createElement('div');
  lhsWrapper.className = 'select mr-2';
  const lhsSelect = document.createElement('select');
  lhsSelect.className = 'condition-variable inline-variable-dropdown';
  lhsSelect.innerHTML = getAllVariableOptionsHTML();
  lhsSelect.onchange = () => renderConditionVariableParams(lhsSelect);
  lhsWrapper.appendChild(lhsSelect);
  row.appendChild(lhsWrapper);

  // LHS params
  const lhsParams = document.createElement('div');
  lhsParams.className = 'condition-parameters mr-2';
  row.appendChild(lhsParams);

  // Operator
  const opWrapper = document.createElement('div');
  opWrapper.className = 'select mr-2';
  const opSelect = document.createElement('select');
  opSelect.className = 'condition-operator';
  opSelect.innerHTML = `
    <option value=">">&gt;</option>
    <option value="<">&lt;</option>
    <option value=">=">&gt;=</option>
    <option value="<=">&lt;=</option>
    <option value="==">==</option>
    <option value="!=">!=</option>
  `;
  opWrapper.appendChild(opSelect);
  row.appendChild(opWrapper);

  // RHS mode + inputs
  const rhsModeWrapper = document.createElement('div');
  rhsModeWrapper.className = 'select mr-2';
  const rhsModeSelect = document.createElement('select');
  rhsModeSelect.className = 'rhs-mode';
  rhsModeSelect.innerHTML = `<option value="value">Value</option><option value="variable">Variable</option>`;
  rhsModeWrapper.appendChild(rhsModeSelect);
  row.appendChild(rhsModeWrapper);

  const rhsValueInput = document.createElement('input');
  rhsValueInput.type = 'text';
  rhsValueInput.className = 'input mr-2 condition-value';
  rhsValueInput.placeholder = 'Value';
  rhsValueInput.style.width = '150px';
  row.appendChild(rhsValueInput);

  const rhsVarWrapper = document.createElement('div');
  rhsVarWrapper.className = 'rhs-input';
  rhsVarWrapper.style.display = 'none';
  rhsVarWrapper.style.alignItems = 'center';
  rhsVarWrapper.style.marginRight = '0.5rem';
  const rhsVarSelect = document.createElement('select');
  rhsVarSelect.className = 'rhs-variable-dropdown inline-variable-dropdown';
  rhsVarSelect.innerHTML = getAllVariableOptionsHTML();
  rhsVarSelect.onchange = () => renderConditionVariableParams(rhsVarSelect);
  rhsVarWrapper.appendChild(rhsVarSelect);
  const rhsParamDiv = document.createElement('div');
  rhsParamDiv.className = 'condition-parameters ml-2';
  rhsVarWrapper.appendChild(rhsParamDiv);
  row.appendChild(rhsVarWrapper);

  // Delete + subgroup
  const deleteBtn = document.createElement('button');
  deleteBtn.className = 'delete';
  deleteBtn.type = 'button';
  deleteBtn.onclick = () => row.remove();
  row.appendChild(deleteBtn);

  const subgroupBtn = document.createElement('button');
  subgroupBtn.className = 'button is-small is-warning ml-2';
  subgroupBtn.type = 'button';
  subgroupBtn.textContent = '➕ Subgroup';
  subgroupBtn.onclick = () => addSubGroupToCondition(subgroupBtn);
  row.appendChild(subgroupBtn);

  // Init RHS state
  rhsModeSelect.value = 'value';
  rhsValueInput.style.display = '';
  rhsVarWrapper.style.display = 'none';

  // Select2 safe
  if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
    $(lhsSelect).select2({ width: 'auto', placeholder: 'Select Variable' });
    $(rhsVarSelect).select2({ width: 'auto', placeholder: 'Select Variable' });
  }

  // ✅ Append to the intended container ONLY
  container.appendChild(row);
}
 
function addSubGroupToCondition(button) {
  const parentRow = button.parentElement;
  if (parentRow.querySelector('.nested-condition')) return;

  const container = document.createElement('div');
  container.classList.add("nested-condition", "ml-4", "mt-2");
  const id = `group_${Math.random().toString(36).substring(2, 8)}`;

  container.innerHTML = `
    <div class="is-flex is-justify-content-space-between mb-2">
      <strong>Nested Subgroup</strong>
      <button type="button" class="delete" onclick="removeSubGroup(this)"></button>
    </div>
    <div class="field">
      <label class="label">Connector</label>
      <div class="select">
        <select class="group-connector">
          <option value="AND">AND</option>
          <option value="OR">OR</option>
        </select>
      </div>
    </div>
    <div class="conditions" id="${id}"></div>
    <button type="button" class="button is-small is-link mt-2" onclick="addConditionRow('${id}')">➕ Add Condition</button>
  `;

  parentRow.appendChild(container);
  button.style.display = 'none';
  button.setAttribute('data-original-display', 'true');
}

function restoreAddSubGroupButton(deleteBtn) {
  const parent = deleteBtn.closest('.condition-row');
  const existingButton = parent.querySelector('button[data-original-text]');
  if (!existingButton) {
    const btn = document.createElement('button');
    btn.className = "button is-small is-warning ml-2";
    btn.textContent = "➕ Subgroup";
    btn.type = "button";
    btn.onclick = function() { addSubGroupToCondition(this); };
    parent.appendChild(btn);
  }
}

function removeSubGroup(deleteBtn) {
  const subgroupDiv = deleteBtn.closest('.nested-condition');
  const parentRow = subgroupDiv.parentElement;
  subgroupDiv.remove();

  const addBtn = parentRow.querySelector('button[data-original-display]');
  if (addBtn) {
    addBtn.style.display = 'inline-block';
    addBtn.removeAttribute('data-original-display');
  } else {
    const newBtn = document.createElement('button');
    newBtn.className = "button is-small is-warning ml-2";
    newBtn.textContent = "➕ Subgroup";
    newBtn.type = "button";
    newBtn.onclick = function () { addSubGroupToCondition(this); };
    parentRow.appendChild(newBtn);
  }
}
function extractConditions(container) {
  // 1) Work inside the current group's .conditions without creating UI
  let rowsContainer;
  if (container.classList.contains('conditions')) {
    rowsContainer = container;
  } else {
    rowsContainer = container.querySelector(':scope > .nested-condition > .conditions');
  }
  if (!rowsContainer) return [];

  // 2) Connector is defined at the group level
  const groupWrap = rowsContainer.closest('.nested-condition');
  const groupConnector = groupWrap?.querySelector('.group-connector')?.value || 'AND';

  const conditions = [];

  // 3) Only pick DIRECT rows of THIS group (no nested!)
  rowsContainer.querySelectorAll(':scope > .condition-row').forEach(row => {
    // LHS
    const variable = row.querySelector('.condition-variable')?.value?.trim();
    if (!variable) return; // skip empty rows

    const operator = row.querySelector('.condition-operator')?.value || '==';

    // LHS parameters (only from this row)
    const lhsParamDiv = row.querySelector(':scope > .condition-parameters');
    const lhsParams = {};
    (lhsParamDiv ? lhsParamDiv.querySelectorAll('input, select') : []).forEach(p => {
      const key = p.dataset.paramKey || p.name.split('_').pop();
      if (p.value !== '') lhsParams[key] = p.value;
    });

    // RHS
    const rhsMode = row.querySelector('.rhs-mode')?.value || 'value';
    let rhs;
    if (rhsMode === 'variable') {
      const rhsVar = row.querySelector('.rhs-variable-dropdown')?.value || '';
      const rhsParamDiv = row.querySelector('.rhs-input .condition-parameters');
      const rhsParams = {};
      (rhsParamDiv ? rhsParamDiv.querySelectorAll('input, select') : []).forEach(p => {
        const key = p.dataset.paramKey || p.name.split('_').pop();
        if (p.value !== '') rhsParams[key] = p.value;
      });
      rhs = { type: 'variable', name: rhsVar, parameters: rhsParams };
    } else {
      const val = row.querySelector('.condition-value')?.value || '';
      rhs = { type: 'value', value: val };
    }

    const cond = {
      lhs: { name: variable, parameters: lhsParams },
      operator,
      rhs,
      connector: groupConnector, // stamp the group's AND/OR
      children: []
    };

    // 4) Recurse ONLY into direct subgroups of THIS row
    row.querySelectorAll(':scope > .nested-condition > .conditions').forEach(subCont => {
      const kids = extractConditions(subCont);
      if (kids.length) cond.children.push(...kids);
    });

    conditions.push(cond);
  });

  return conditions;
}


function addRootCondition(containerId, button) {
  const container = document.getElementById(containerId);
  if (container.querySelector('.nested-condition')) return;

  const div = document.createElement('div');
  div.classList.add("nested-condition", "mt-2");
  const id = `group_${Math.random().toString(36).substring(2, 8)}`;

  div.innerHTML = `
    <div class="is-flex is-justify-content-space-between mb-2">
      <strong>Condition</strong>
      <button type="button" class="delete" onclick="removeRootCondition('${containerId}', this)"></button>
    </div>
    <div class="field">
      <label class="label">Connector</label>
      <div class="select">
        <select class="group-connector">
          <option value="AND">AND</option>
          <option value="OR">OR</option>
        </select>
      </div>
    </div>
    <div class="conditions" id="${id}"></div>
    <button type="button" class="button is-small is-link mt-2" onclick="addConditionRow('${id}')">➕ Add Condition</button>
  `;
  container.appendChild(div);
  button.style.display = 'none';
  button.setAttribute('data-root-btn', 'true');
}

function removeRootCondition(containerId, deleteBtn) {
  const block = deleteBtn.closest('.nested-condition');
  const parent = document.getElementById(containerId);
  block.remove();

  const existing = parent.parentElement.querySelector('button[data-root-btn]');
  if (existing) {
    existing.style.display = 'inline-block';
    existing.removeAttribute('data-root-btn');
  } else {
    const newBtn = document.createElement('button');
    newBtn.className = "button is-small is-link mt-2";
    newBtn.textContent = "➕ Condition";
    newBtn.type = "button";
    newBtn.onclick = function () { addRootCondition(containerId, this); };
    parent.appendChild(newBtn);
  }
}
function restoreConditionTree(containerIdOrEl, conditions) {
  const host = (typeof containerIdOrEl === 'string') ? document.getElementById(containerIdOrEl) : containerIdOrEl;
  if (!host) return;

  // Work inside this group's .conditions container (create root group if needed)
  const rowsContainer = getRowsContainer(host);
  if (!rowsContainer) return;

  // Clear only direct rows of THIS group
  rowsContainer.querySelectorAll(':scope > .condition-row').forEach(r => r.remove());

  // Set the group connector from the first cond, if present
  const groupWrap = rowsContainer.closest('.nested-condition');
  if (groupWrap && conditions?.length) {
    const connSel = groupWrap.querySelector('.group-connector');
    if (connSel) connSel.value = conditions[0].connector || 'AND';
  }

  conditions.forEach((cond, idx) => {
    // Add a fresh row to THIS group
    addConditionRow(rowsContainer);   // pass element, not id
    const row = rowsContainer.querySelector(':scope > .condition-row:last-of-type');
    if (!row) return;

    // LHS variable + params
    const lhsSel = row.querySelector('.condition-variable');
    if (lhsSel) {
      if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
        $(lhsSel).val(cond.lhs?.name || '').trigger('change.select2');
      } else {
        lhsSel.value = cond.lhs?.name || '';
        lhsSel.dispatchEvent(new Event('change', { bubbles: true }));
      }
      renderConditionVariableParams(lhsSel);

      // symbol first
      const symSel = row.querySelector(':scope > .condition-parameters .symbol-dropdown');
      const symVal = cond.lhs?.parameters?.symbol;
      if (symSel && symVal) {
        initSelect2(`#${symSel.id || (symSel.id = 'sym_'+Math.random().toString(36).slice(2,8))}`, "Select symbol");
        if (![...symSel.options].some(o => o.value === symVal)) symSel.add(new Option(symVal, symVal, true, true));
        if (typeof $ !== 'undefined') $(symSel).val(symVal).trigger('change.select2');
      }
      // other params
      Object.entries(cond.lhs?.parameters || {}).forEach(([k, v]) => {
        if (k === 'symbol') return;
        const inp = row.querySelector(`:scope > .condition-parameters [name$="${k}"]`);
        if (inp) inp.value = v;
      });
    }

    // Operator
    const opSel = row.querySelector('.condition-operator');
    if (opSel) opSel.value = cond.operator || '==';

    // RHS
    const rhsModeSel = row.querySelector('.rhs-mode');
    if (rhsModeSel) {
      rhsModeSel.value = cond.rhs?.type || 'value';
      rhsModeSel.dispatchEvent(new Event('change', { bubbles: true }));

      if (cond.rhs?.type === 'value') {
        const valInp = row.querySelector('.condition-value');
        if (valInp) valInp.value = cond.rhs.value ?? '';
      } else {
        const rhsVarSelect = row.querySelector('.rhs-variable-dropdown');
        if (rhsVarSelect) {
          if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
            $(rhsVarSelect).val(cond.rhs?.name || '').trigger('change.select2');
          } else {
            rhsVarSelect.value = cond.rhs?.name || '';
            rhsVarSelect.dispatchEvent(new Event('change', { bubbles: true }));
          }
          renderConditionVariableParams(rhsVarSelect);

          // RHS symbol
          const rhsSym = row.querySelector('.rhs-input .symbol-dropdown');
          const rhsSymVal = cond.rhs?.parameters?.symbol;
          if (rhsSym && rhsSymVal) {
            initSelect2(`#${rhsSym.id || (rhsSym.id = 'rsym_'+Math.random().toString(36).slice(2,8))}`, "Select symbol");
            if (![...rhsSym.options].some(o => o.value === rhsSymVal)) rhsSym.add(new Option(rhsSymVal, rhsSymVal, true, true));
            if (typeof $ !== 'undefined') $(rhsSym).val(rhsSymVal).trigger('change.select2');
          }
          // other RHS params
          Object.entries(cond.rhs?.parameters || {}).forEach(([k, v]) => {
            if (k === 'symbol') return;
            const inp = row.querySelector(`.rhs-input [name$="${k}"]`);
            if (inp) inp.value = v;
          });
        }
      }
    }

    // Nested children → create ONE subgroup under THIS row and recurse into its .conditions
    if (Array.isArray(cond.children) && cond.children.length) {
      const addSubBtn = row.querySelector('.button.is-small.is-warning');
      if (addSubBtn) {
        addSubGroupToCondition(addSubBtn);
        const subCont = row.querySelector(':scope > .nested-condition > .conditions');
        if (subCont) restoreConditionTree(subCont, cond.children); // pass element
      }
    }
  });
}

function restoreConditionTreeOld(containerId, conditions) {
  const container = document.getElementById(containerId);
  // “Open” the root condition group if it isn’t already
  const rootBtn = container.querySelector('button[data-root-btn]');
  if (rootBtn) rootBtn.click();

  const target = container.querySelector('.conditions');
  if (!target) return;

  conditions.forEach(cond => {
    // 1) Create the row wrapper
    const row = document.createElement('div');
    row.className = 'condition-row is-flex is-align-items-center mb-2';

    // 2) LHS variable dropdown
    const varDropdown = document.createElement('select');
    varDropdown.className = 'condition-variable inline-variable-dropdown';
    varDropdown.innerHTML = getAllVariableOptionsHTML();
    varDropdown.value = cond.lhs.name;
    varDropdown.onchange = () => renderConditionVariableParams(varDropdown);
    row.appendChild(wrapElement(varDropdown));

    // 3) LHS parameters container
    const paramWrapper = document.createElement('div');
    paramWrapper.className = 'condition-parameters mr-2';
    row.appendChild(paramWrapper);

    // populate any saved LHS params
    renderConditionVariableParams(varDropdown);
    for (const [key, val] of Object.entries(cond.lhs.parameters || {})) {
      const input = paramWrapper.querySelector(`[name$="${key}"]`);
      if (input) input.value = val;
    }

    // 4) Operator dropdown
    const opSelect = document.createElement('select');
    opSelect.className = 'condition-operator';
    opSelect.innerHTML = `
      <option value=">">&gt;</option>
      <option value="<">&lt;</option>
      <option value=">=">&gt;=</option>
      <option value="<=">&lt;=</option>
      <option value="==">==</option>
      <option value="!=">!=</option>
    `;
    opSelect.value = cond.operator;
    row.appendChild(wrapElement(opSelect));

    // 5) RHS-mode selector
    const rhsModeSelect = document.createElement('select');
    rhsModeSelect.className = 'rhs-mode';
    rhsModeSelect.innerHTML = `
      <option value="value">Value</option>
      <option value="variable">Variable</option>
    `;
    rhsModeSelect.value = cond.rhs.type;
    row.appendChild(wrapElement(rhsModeSelect));

    // 6) RHS text-input
    const rhsValueInput = document.createElement('input');
    rhsValueInput.type = 'text';
    rhsValueInput.className = 'condition-value input';
    rhsValueInput.style.width = '100px';
    rhsValueInput.value = cond.rhs.type === 'value' ? cond.rhs.value : '';
    row.appendChild(rhsValueInput);

    // 7) RHS variable dropdown wrapper
    const rhsVarWrapper = document.createElement('div');
    rhsVarWrapper.className = 'rhs-input';
    // hide or show based on saved type
    rhsVarWrapper.style.display = cond.rhs.type === 'variable' ? '' : 'none';
    const rhsVarSelect = document.createElement('select');
    rhsVarSelect.className = 'rhs-variable-dropdown';
    rhsVarSelect.innerHTML = getAllVariableOptionsHTML();
    rhsVarSelect.value = cond.rhs.name || '';
    rhsVarSelect.onchange = () => renderConditionVariableParams(rhsVarSelect);
    rhsVarWrapper.appendChild(rhsVarSelect);
    row.appendChild(rhsVarWrapper);

    // 8) Fire a “change” so the global delegate toggles visibility
    rhsModeSelect.dispatchEvent(new Event('change', { bubbles: true }));

    // 9) Delete & Subgroup buttons
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'delete';
    deleteBtn.type = 'button';
    deleteBtn.onclick = () => row.remove();
    row.appendChild(deleteBtn);

    const subgroupBtn = document.createElement('button');
    subgroupBtn.className = 'button is-small is-warning ml-2';
    subgroupBtn.type = 'button';
    subgroupBtn.textContent = '➕ Subgroup';
    subgroupBtn.onclick = () => addSubGroupToCondition(subgroupBtn);
    row.appendChild(subgroupBtn);

    // 10) Apply Select2 on any inline-variable-dropdowns
    $(row).find('.inline-variable-dropdown').select2({
      width: 'auto',
      placeholder: 'Select Variable'
    });

    // 11) Add the row to the DOM
    target.appendChild(row);

    // 12) Recursively restore any nested children
    if (cond.children?.length) {
      addSubGroupToCondition(subgroupBtn);
      const subContainer = row.querySelector('.nested-condition .conditions');
      restoreConditionTree(subContainer.id, cond.children);
    }
  });
}

  // Expression builder param renderer (used by addExpressionVariable)
function renderInlineVariableParams(selectEl, index) {
  // Find the parameters container for the expression item
  const field = selectEl.closest('.field'); // in expression builder, select is inside .field.box...
  const paramTarget = field ? field.querySelector('.parameters') : null;
  if (!paramTarget) return;

  paramTarget.innerHTML = '';

  const variableName = selectEl.value;
  if (!variableName) return;

  // Try both indicators and userDefinedVariables (for UDV dependency chains)
  const variable =
    (Array.isArray(indicators) && indicators.find(i => i.name === variableName)) ||
    (Array.isArray(userDefinedVariables) && userDefinedVariables.find(v => v.name === variableName));

  if (!variable) {
    // Unknown variable selected
    const msg = document.createElement('div');
    msg.className = 'has-text-danger has-text-weight-semibold';
    msg.textContent = '⚠️ Unknown variable selected.';
    paramTarget.appendChild(msg);
    return;
  }

  // User-defined variables usually have no declared parameters
  if (!Array.isArray(variable.parameters) || variable.parameters.length === 0) {
    const msg = document.createElement('div');
    msg.className = 'has-text-grey-light is-size-7 is-italic mt-1';
    msg.textContent = 'No parameters required.';
    paramTarget.appendChild(msg);
    return;
  }

  // Helper to pick a default value, with common fallbacks
  const getDefault = (param) =>
    param.default_value ?? param.default ?? param.defaultValue ?? param.example ?? '';

  // Render each parameter with defaults/choices/type
  variable.parameters.forEach(param => {
    const pname = (param.name || '').toString();
    const lower = pname.toLowerCase();
    const defVal = getDefault(param);
    const inputName = `const_expr_${index}_${variable.name}_${pname}`;

    // SYMBOL → Select2 dropdown (with optional default)
    if (lower === 'symbol') {
      const symbolSelectId = `symbol_select_${index}_${Date.now()}`;
      const symbolDropdown = document.createElement('select');
      symbolDropdown.name = inputName;
      symbolDropdown.className = 'symbol-dropdown select is-small mt-1';
      symbolDropdown.id = symbolSelectId;
      paramTarget.appendChild(symbolDropdown);

      // init AJAX select2
      if (typeof initSelect2 === 'function') {
        initSelect2(`#${symbolSelectId}`, 'Select symbol');
      }

      // If there is a default symbol, inject & select it even if not in the AJAX list
      if (defVal !== '' && defVal != null) {
        symbolDropdown.add(new Option(defVal, defVal, true, true));
        if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
          $(symbolDropdown).val(defVal).trigger('change.select2');
        }
      }
      return; // done with symbol
    }

    // If param has discrete choices, render a <select>
    if (Array.isArray(param.choices) && param.choices.length > 0) {
      const wrap = document.createElement('div');
      wrap.className = 'select is-small mt-1';
      const sel = document.createElement('select');
      sel.name = inputName;

      // Optional empty placeholder if no default
      if (defVal === '' || defVal == null) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = `Select ${pname}`;
        sel.appendChild(opt);
      }

      param.choices.forEach(choice => {
        // choices may be ['1m','5m'] or [{value:'1m', label:'1 min'}]
        const value = (choice && typeof choice === 'object') ? (choice.value ?? choice.key ?? choice.name ?? choice.label) : choice;
        const label = (choice && typeof choice === 'object') ? (choice.label ?? choice.name ?? choice.value ?? String(value)) : String(choice);
        const opt = document.createElement('option');
        opt.value = value;
        opt.textContent = label;
        if (defVal != null && String(value) === String(defVal)) opt.selected = true;
        sel.appendChild(opt);
      });

      wrap.appendChild(sel);
      paramTarget.appendChild(wrap);
      return;
    }

    // Otherwise, render an <input> and prefill default
    const input = document.createElement('input');
    input.className = 'input is-small mt-1';
    input.placeholder = pname;
    input.name = inputName;

    // Basic type hinting
    const t = (param.type || '').toString().toLowerCase();
    if (t.includes('int') || t.includes('float') || t.includes('number')) {
      input.type = 'number';
      if (param.min != null) input.min = param.min;
      if (param.max != null) input.max = param.max;
      if (param.step != null) input.step = param.step;
    } else {
      input.type = 'text';
    }

    // Prefill default value
    if (defVal !== undefined && defVal !== null) {
      input.value = defVal;
    }

    paramTarget.appendChild(input);
  });

  // keep your validation in sync
  if (typeof validateExpressionBuilder === 'function') {
    validateExpressionBuilder(index);
  }
}

function renderConditionVariableParams(selectEl) {
  const variableName = selectEl.value;
  const container = selectEl.closest('.condition-row');

  // Determine if LHS or RHS
  const isRHS = selectEl.classList.contains("rhs-variable-dropdown");

  // Target correct parameter container
  let paramDiv;
  if (isRHS) {
    // RHS container is deeper nested
    paramDiv = container.querySelector('.rhs-input .condition-parameters');
  } else {
    paramDiv = container.querySelector('.condition-parameters');
  }

  if (!paramDiv) return;
  paramDiv.innerHTML = '';

  if (!variableName) return;

  // Search in both indicators and userDefinedVariables
  const variable =
    indicators.find(i => i.name === variableName) ||
    userDefinedVariables.find(v => v.name === variableName);

  if (!variable) {
    const warning = document.createElement('div');
    warning.className = 'has-text-danger has-text-weight-semibold';
    warning.textContent = "⚠️ Unknown variable selected.";
    paramDiv.appendChild(warning);
    return;
  }

  if (!variable.parameters || variable.parameters.length === 0) {
    const msg = document.createElement('div');
    msg.className = 'has-text-grey-light is-size-7 is-italic mt-1';
    msg.textContent = 'No parameters required.';
    paramDiv.appendChild(msg);
    return;
  }

  // Render required inputs
  variable.parameters.forEach(param => {
    if (param.name.toLowerCase() === 'symbol') {
      const selectId = `cond_symbol_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
      const select = document.createElement('select');
      select.name = `cond_param_${variableName}_${param.name}`;
      select.id = selectId;
      select.className = 'symbol-dropdown input is-small mt-1';
      paramDiv.appendChild(select);
      initSelect2(`#${selectId}`, "Select symbol");
    } else {
      const input = document.createElement('input');
      input.className = 'input is-small mt-1';
      input.placeholder = param.name;
      input.name = `cond_param_${variableName}_${param.name}`;
      input.value = param.default_value || "";
      paramDiv.appendChild(input);
    }
  });
}

// Helper assumed elsewhere in your code:
function wrapElement(el) {
  const wrapper = document.createElement('div');
  wrapper.className = 'select mr-2';
  wrapper.appendChild(el);
  return wrapper;
}



