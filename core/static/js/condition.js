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
  // 1) Locate the .conditions container
  let container;
  if (typeof target === 'string') {
    container = document.getElementById(target);
  } else {
    container = target.closest('.nested-condition')?.querySelector('.conditions');
  }
  if (!container) return;

  // 2) If this group isn't wrapped yet, wrap it and bail
  const isWrapped = container.closest('.nested-condition');
  if (!isWrapped) {
    const wrapper = document.createElement('div');
    wrapper.classList.add("box", "nested-condition", "mt-3");
    const groupId = `group_${Math.random().toString(36).substring(2, 8)}`;
    wrapper.innerHTML = `
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
      <div class="conditions" id="${groupId}"></div>
      <button type="button" class="button is-small is-link mt-2" onclick="addConditionRow('${groupId}')">➕ Add Condition</button>
    `;
    container.appendChild(wrapper);
    return;
  }

  // 3) Build a new condition-row
  const row = document.createElement('div');
  row.classList.add('condition-row', 'is-flex', 'is-align-items-center', 'mb-2');

  // — LHS variable dropdown
  const lhsWrapper = document.createElement('div');
  lhsWrapper.className = 'select mr-2';
  const lhsSelect = document.createElement('select');
  lhsSelect.className = 'condition-variable inline-variable-dropdown';
  lhsSelect.innerHTML = getAllVariableOptionsHTML();
  lhsSelect.onchange = () => renderConditionVariableParams(lhsSelect);
  lhsWrapper.appendChild(lhsSelect);
  row.appendChild(lhsWrapper);

  // — LHS parameters container
  const lhsParams = document.createElement('div');
  lhsParams.className = 'condition-parameters mr-2';
  row.appendChild(lhsParams);

  // — Operator dropdown
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

  // — RHS Mode selector
  const rhsModeWrapper = document.createElement('div');
  rhsModeWrapper.className = 'select mr-2';
  const rhsModeSelect = document.createElement('select');
  rhsModeSelect.className = 'rhs-mode';
  rhsModeSelect.innerHTML = `
    <option value="value">Value</option>
    <option value="variable">Variable</option>
  `;
  rhsModeWrapper.appendChild(rhsModeSelect);
  row.appendChild(rhsModeWrapper);

  // — RHS value input
  const rhsValueInput = document.createElement('input');
  rhsValueInput.type = 'text';
  rhsValueInput.className = 'input mr-2 condition-value';
  rhsValueInput.placeholder = 'Value';
  rhsValueInput.style.width = '150px';
  row.appendChild(rhsValueInput);

  // — RHS variable dropdown + params wrapper
  const rhsVarWrapper = document.createElement('div');
  // use inline-flex so it doesn't become a full-width block
  rhsVarWrapper.className = 'rhs-input';
  rhsVarWrapper.style.display = 'none';
  rhsVarWrapper.style.cssText += 'display:none; align-items:center; margin-right:0.5rem; display:inline-flex;';
  const rhsVarSelect = document.createElement('select');
  rhsVarSelect.className = 'rhs-variable-dropdown inline-variable-dropdown';
  rhsVarSelect.innerHTML = getAllVariableOptionsHTML();
  rhsVarSelect.onchange = () => renderConditionVariableParams(rhsVarSelect);
  rhsVarWrapper.appendChild(rhsVarSelect);
  // parameters under RHS variable
  const rhsParamDiv = document.createElement('div');
  rhsParamDiv.className = 'condition-parameters ml-2';
  rhsVarWrapper.appendChild(rhsParamDiv);
  row.appendChild(rhsVarWrapper);

  // — Delete button
  const deleteBtn = document.createElement('button');
  deleteBtn.className = 'delete';
  deleteBtn.type = 'button';
  deleteBtn.onclick = () => row.remove();
  row.appendChild(deleteBtn);

  // — Subgroup button
  const subgroupBtn = document.createElement('button');
  subgroupBtn.className = 'button is-small is-warning ml-2';
  subgroupBtn.type = 'button';
  subgroupBtn.textContent = '➕ Subgroup';
  subgroupBtn.onclick = () => addSubGroupToCondition(subgroupBtn);
  row.appendChild(subgroupBtn);

  // initialize
  rhsModeSelect.value = 'value';
  rhsValueInput.style.display = '';
  rhsVarWrapper.style.display = 'none';

  // 5) Activate Select2 on both dropdowns
  $(lhsSelect).select2({ width: 'auto', placeholder: 'Select Variable' });
  $(rhsVarSelect).select2({ width: 'auto', placeholder: 'Select Variable' });

  // 6) Finally append the row
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
  const conditions = [];
  const rows = container.querySelectorAll('.condition-row');
  rows.forEach(row => {
    const variable = row.querySelector('.condition-variable')?.value;
    const operator = row.querySelector('.condition-operator')?.value;
    const connector = row.closest('.nested-condition')?.querySelector('.group-connector')?.value || 'AND';

    // LHS Parameters
    const paramDiv = row.querySelector('.condition-parameters');
    const paramInputs = paramDiv ? paramDiv.querySelectorAll('input, select') : [];
    const lhsParams = {};
    paramInputs.forEach(p => {
      const key = p.name.split('_').pop();
      lhsParams[key] = p.value;
    });

    // RHS: either value or variable
    const rhsType = row.querySelector('.rhs-mode')?.value || 'value';
    let rhs = { type: rhsType };
    if (rhsType === 'value') {
      rhs.value = row.querySelector('.condition-value')?.value || '';
    } else {
      const rhsVar = row.querySelector('.rhs-variable-dropdown')?.value;
      const rhsParamDiv = row.querySelector('.rhs-variable-dropdown')?.closest('.rhs-input')?.querySelectorAll('input, select');
      const rhsParams = {};
      rhsParamDiv?.forEach(p => {
        const key = p.name?.split('_')?.pop();
        rhsParams[key] = p.value;
      });
      rhs.name = rhsVar;
      rhs.parameters = rhsParams;
    }

    const cond = {
      lhs: {
        name: variable,
        parameters: lhsParams
      },
      operator,
      rhs,
      connector,
      children: []
    };

    // Try to find all nested condition containers directly under this row
    const subgroups = row.querySelectorAll(':scope > .nested-condition > .conditions');
    subgroups.forEach(subContainer => {
      cond.children.push(...extractConditions(subContainer));
    });

    // (Fallback: If only a single nested condition per row, keep your original logic)
    // const subContainer = row.querySelector('.nested-condition .conditions');
    // if (subContainer) {
    //   cond.children = extractConditions(subContainer);
    // }

    conditions.push(cond);
    // Log what is being extracted for debugging
    console.log("Extracted condition:", cond);
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
function restoreConditionTree(containerId, conditions) {
  const container = document.getElementById(containerId);
  if (!container) {
    console.error("restoreConditionTree: no container for", containerId);
    return;
  }

  // Determine where .condition-row elements live
  const rowsContainer = container.classList.contains('conditions')
    ? container
    : (container.querySelector('.conditions') || container);

  // Remove any pre-existing rows
  Array.from(rowsContainer.querySelectorAll('.condition-row'))
    .forEach(r => r.remove());

  // “Open” the root condition group if needed
  const rootBtn = container.querySelector('button[data-root-btn]');
  if (rootBtn) rootBtn.click();

  // Rebuild each condition
  conditions.forEach((cond, idx) => {
    console.log(`restore condition[${idx}] in ${containerId}`, cond);

    // 1) Add a new row into this container
    addConditionRow(rowsContainer.id);
    const row = rowsContainer.querySelector('.condition-row:last-of-type');
    if (!row) {
      console.error("Could not create row for", cond);
      return;
    }

    // ─── LHS: variable + parameters ───────────────────────────────────────────
    const lhsSel = row.querySelector('.condition-variable');
    if (lhsSel) {
      // Select the variable via Select2 (or fallback)
      if (typeof $ !== 'undefined' && $(lhsSel).select2) {
        $(lhsSel).val(cond.lhs.name || '').trigger('change.select2');
      } else {
        lhsSel.value = cond.lhs.name || '';
      }

      // Render its parameter inputs
      renderConditionVariableParams(lhsSel);

      // Populate the symbol parameter first
      const symSel = row.querySelector('.condition-parameters .symbol-dropdown');
      const symVal = cond.lhs.parameters.symbol;
      if (symSel && symVal) {
        initSelect2(`#${symSel.id}`, "Select symbol");
        if (![...symSel.options].some(o => o.value === symVal)) {
          symSel.add(new Option(symVal, symVal, true, true));
        }
        $(symSel).trigger('change');
      }

      // Populate any other LHS params
      Object.entries(cond.lhs.parameters || {}).forEach(([k, v]) => {
        if (k === 'symbol') return;
        const inp = row.querySelector(`.condition-parameters [name$="${k}"]`);
        if (inp) inp.value = v;
      });
    } else {
      console.warn("No LHS variable dropdown in row", idx);
    }

    // ─── Operator ─────────────────────────────────────────────────────────────
    const opSel = row.querySelector('.condition-operator');
    if (opSel) opSel.value = cond.operator;

    // ─── Connector ────────────────────────────────────────────────────────────
    const grpWrap = row.closest('.nested-condition');
    if (grpWrap) {
      const connSel = grpWrap.querySelector('.group-connector');
      if (connSel) connSel.value = cond.connector;
    }

    // ─── RHS: value vs variable ────────────────────────────────────────────────
    const rhsModeSel = row.querySelector('.rhs-mode');
    if (rhsModeSel) {
      rhsModeSel.value = cond.rhs.type || 'value';
      rhsModeSel.dispatchEvent(new Event('change', { bubbles: true }));

      if (cond.rhs.type === 'value') {
        const valInp = row.querySelector('.condition-value');
        if (valInp) valInp.value = cond.rhs.value;
      } else {
        // Variable case
        const varSel = row.querySelector('.rhs-variable-dropdown');
        if (varSel) {
          if (typeof $ !== 'undefined' && $(varSel).select2) {
            $(varSel).val(cond.rhs.name || '').trigger('change.select2');
          } else {
            varSel.value = cond.rhs.name || '';
          }

          // Render its parameters
          renderConditionVariableParams(varSel);

          // Populate the RHS symbol param
          const rhsSym = row.querySelector('.rhs-input .symbol-dropdown');
          const rhsSymVal = cond.rhs.parameters.symbol;
          if (rhsSym && rhsSymVal) {
            initSelect2(`#${rhsSym.id}`, "Select symbol");
            if (![...rhsSym.options].some(o => o.value === rhsSymVal)) {
              rhsSym.add(new Option(rhsSymVal, rhsSymVal, true, true));
            }
            $(rhsSym).trigger('change');
          }

          // Populate any other RHS params
          Object.entries(cond.rhs.parameters || {}).forEach(([k, v]) => {
            if (k === 'symbol') return;
            const inp = row.querySelector(`.rhs-input [name$="${k}"]`);
            if (inp) inp.value = v;
          });
        } else {
          console.warn("No RHS variable dropdown in row", idx);
        }
      }
    } else {
      console.warn("No RHS mode selector in row", idx);
    }

    // ─── Nested Subgroups ──────────────────────────────────────────────────────
    if (Array.isArray(cond.children) && cond.children.length) {
      console.log(`  → ${cond.children.length} nested children for row ${idx}`);
      const subBtn = row.querySelector('button.is-small.is-warning');
      if (subBtn) {
        addSubGroupToCondition(subBtn);
        const subCont = row.querySelector('.nested-condition .conditions');
        if (subCont) {
          restoreConditionTree(subCont.id, cond.children);
        } else {
          console.warn("No sub-conditions container in row", idx);
        }
      } else {
        console.warn("No subgroup button in row", idx);
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

  function renderInlineVariableParams(selectEl, index) {
    const variableName = selectEl.value;
    const paramTarget = selectEl.closest('.field').querySelector('.parameters');
    paramTarget.innerHTML = '';

    const variable = indicators.find(i => i.name === variableName);
    if (!variable || !variable.parameters) return;

    variable.parameters.forEach(param => {
      if (param.name.toLowerCase() === 'symbol') {
        const symbolSelectId = `symbol_select_${index}_${Date.now()}`;
        const symbolDropdown = document.createElement('select');
        symbolDropdown.name = `const_expr_${index}_${variable.name}_${param.name}`;
        symbolDropdown.className = 'symbol-dropdown select is-small mt-1';
        symbolDropdown.id = symbolSelectId;
        paramTarget.appendChild(symbolDropdown);
        initSelect2(`#${symbolSelectId}`, "Select symbol");
      } else {
        const input = document.createElement('input');
        input.className = 'input is-small mt-1';
        input.placeholder = `${param.name}`;
        input.name = `const_expr_${index}_${variable.name}_${param.name}`;
        paramTarget.appendChild(input);
      }
    });
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



