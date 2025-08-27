// ---- expression param helpers (global) ----
const PARAM_ALIASES = {
  lookup: 'lookback',
  look_up: 'lookback',
  time_frame: 'timeframe',
  tf: 'timeframe',
};

function toParamList(params) {
  if (Array.isArray(params)) return params;
  if (params && typeof params === 'object') {
    return Object.entries(params).map(([k, v]) => ({ key: k, value: v }));
  }
  return [];
}
function ensureEditorHeader(index) {
  const box = document.getElementById(`user_constant_box_${index}`);
  if (!box) return;

  let header = box.querySelector('.user-const-header');
  if (!header) {
    header = document.createElement('div');
    header.className = 'user-const-header is-flex is-justify-content-space-between is-align-items-center mb-2';
    header.innerHTML = `
      <strong>Variable Definition</strong>
      <button type="button"
              class="delete"
              id="user_variable_close_${index}"
              title="Delete variable"
              onclick="removeUserConstant(${index})"></button>
    `;
    box.insertBefore(header, box.firstChild);
  } else {
    // make sure the button is visible when editing
    header.style.display = '';
  }
}

function findParamControl(paramsDiv, key) {
  if (!paramsDiv) return null;
  let keyLower = String(key || '').toLowerCase();
  if (PARAM_ALIASES[keyLower]) keyLower = PARAM_ALIASES[keyLower];

  // Preferred: match by data-param-key set on inputs/selects
  let el = paramsDiv.querySelector(`[data-param-key="${keyLower}"]`);
  if (el) return el;

  // Fallback: case-insensitive "name ends with"
  const all = paramsDiv.querySelectorAll('input, select');
  for (const c of all) {
    const nm = (c.name || '').toLowerCase();
    if (nm.endsWith(keyLower)) return c;
  }
  return null;
}

function setSelect2Value(sel, value) {
  const val = String(value ?? '');
  if (!val) return;

  if (![...sel.options].some(o => o.value === val)) {
    sel.add(new Option(val, val, true, true));
  }

  const apply = () => {
    if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
      if ($(sel).hasClass('select2-hidden-accessible')) {
        $(sel).val(val).trigger('change.select2');
      } else {
        $(sel).select2();
        $(sel).val(val).trigger('change.select2');
      }
    } else {
      sel.value = val;
      sel.dispatchEvent(new Event('change', { bubbles: true }));
    }
  };
  apply();
  setTimeout(apply, 0);
  setTimeout(apply, 60);
}




function getVarBox(index) {
  return document.getElementById(`user_constant_box_${index}`);
}

function getHiddenInput(index) {
  const box = getVarBox(index);
  if (!box) return null;

  // Keep ONE hidden input inside the box
  let hidden = box.querySelector(`#user_constant_input_${index}`);
  if (!hidden) {
    hidden = document.createElement("input");
    hidden.type = "hidden";
    hidden.name = `user_variable_json_${index}`;
    hidden.id   = `user_constant_input_${index}`;
    box.appendChild(hidden);
  }

  // Clean up dupes that might exist elsewhere (e.g. under #algoForm)
  document.querySelectorAll(`#user_constant_input_${index}`).forEach(el => {
    if (el !== hidden && !box.contains(el)) el.remove();
  });

  return hidden;
}


function addUserDefinedVariable() {
  const container = document.getElementById('userConstantsContainer');
  const index = container.children.length;

  const box = document.createElement('div');
  box.classList.add('box', 'mb-3');
  box.id = `user_constant_box_${index}`;
  box.innerHTML = `
    <div class="udv-header is-flex is-justify-content-space-between is-align-items-center mb-2">
      <strong>Variable Definition</strong>
      <div class="is-flex is-align-items-center">
        <span id="constant_status_${index}" class="icon is-small mr-2"></span>
        <button type="button" class="delete" 
              onclick="this.closest('.box').remove()">
      </button>
      </div>
    </div>

    <div class="field">
      <label class="label">Variable Name</label>
      <input class="input" name="user_constant_name_${index}" placeholder="e.g., Variable1" data-original-name="">
      <p id="var_name_error_${index}" class="help is-danger" style="display:none;"></p>
    </div>

    <div id="expression_builder_${index}" class="expression_builder is-flex is-align-items-center is-flex-wrap-wrap mb-3"></div>
    <p id="const_preview_${index}" class="is-size-7 has-text-grey mt-1 ml-1"></p>

    <div class="buttons udv-toolbar mb-2">
      <button type="button" class="button is-small is-primary" onclick="addExpressionVariable(${index})">➕ Variable</button>
      <button type="button" class="button is-small is-info" onclick="addExpressionOperator(${index})">➕ Operator</button>
      <button type="button" class="button is-small is-link" onclick="addExpressionValue(${index})">➕ Value</button>
    </div>

    <button type="button" class="button is-small is-success" onclick="saveUserConstant(${index})">💾 Save Variable</button>
  `;

  container.appendChild(box);
box.querySelector(`input[name="user_constant_name_${index}"]`).dataset.originalName = "";

  // Add real-time validation on name input
  const nameInput = box.querySelector(`input[name="user_constant_name_${index}"]`);
  const errorText = box.querySelector(`#var_name_error_${index}`);

  nameInput.addEventListener("input", function () {
  const name = nameInput.value.trim();
  const allInputs = document.querySelectorAll('input[name^="user_constant_name_"]');
  let duplicate = false;

  for (const inp of allInputs) {
    if (inp !== nameInput && inp.value.trim() === name) {
      duplicate = true;
      break;
    }
  }

  const existsInPredefined = userDefinedVariables.some(v => v.name === name);
  const errorText = document.getElementById(`var_name_error_${index}`);
  const saveBtn = document.querySelector(`#user_constant_box_${index} button[onclick^="saveUserConstant"]`);

  if (!name) {
    nameInput.classList.add("is-danger");
    errorText.textContent = "Variable name cannot be empty.";
    errorText.style.display = "block";
    if (saveBtn) saveBtn.disabled = true;
  } else if (duplicate || existsInPredefined) {
    nameInput.classList.add("is-danger");
    errorText.textContent = "Variable name already exists.";
    errorText.style.display = "block";
    if (saveBtn) saveBtn.disabled = true;
  } else {
    nameInput.classList.remove("is-danger");
    errorText.style.display = "none";
    errorText.textContent = "";
    if (saveBtn) saveBtn.disabled = false;
  }
});

}
function loadExpressionUIFromJSON(containerId, expressionData) {
  const container = document.getElementById(containerId);
  if (!container || !Array.isArray(expressionData)) return;

  container.innerHTML = ''; // Clear any previous content

  expressionData.forEach((part, idx) => {
    let elementWrapper = document.createElement('div');
    elementWrapper.classList.add('control');

    // ➕ Variable
    if (part.type === 'variable') {
      const select = document.createElement('select');
      select.classList.add('select', 'is-small', 'expression-part');
      select.dataset.partType = 'variable';

      const emptyOpt = document.createElement('option');
      emptyOpt.value = '';
      emptyOpt.textContent = 'Select Variable';
      select.appendChild(emptyOpt);

      userDefinedVariables.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.name;
        opt.textContent = v.name;
        if (v.name === part.value) opt.selected = true;
        select.appendChild(opt);
      });

      elementWrapper.appendChild(select);
    }

    // ➕ Operator
    else if (part.type === 'operator') {
      const input = document.createElement('input');
      input.classList.add('input', 'is-small', 'expression-part');
      input.placeholder = 'Operator';
      input.dataset.partType = 'operator';
      input.value = part.value || '';
      elementWrapper.appendChild(input);
    }

    // ➕ Value
    else if (part.type === 'value') {
      const input = document.createElement('input');
      input.classList.add('input', 'is-small', 'expression-part');
      input.placeholder = 'Value';
      input.dataset.partType = 'value';
      input.value = part.value || '';
      elementWrapper.appendChild(input);
    }

    // ➕ Constant (Read-only label)
    else if (part.type === 'constant') {
      const span = document.createElement('span');
      span.classList.add('tag', 'is-info');
      span.textContent = part.value || '[constant]';
      elementWrapper.appendChild(span);
    }

    // Add to container
    container.appendChild(elementWrapper);
  });
}

function buildExpressionFromUI(index) {
  const container = document.getElementById(`expression_builder_${index}`);
  const parts = [];

  container.querySelectorAll('.expression-part').forEach(el => {
    const type = el.dataset.partType;
    const value = el.value?.trim();

    if (value) {
      parts.push({ type, value });
    }
  });

  return parts;
}

function addExpressionVariable(index) {
  const target = document.getElementById(`expression_builder_${index}`);
  const wrapper = document.createElement('div');
  wrapper.classList.add('expression-item');

  // Group and sort indicators by category
  const grouped = {};
  indicators.forEach(v => {
    const cat = v.category || "uncategorized";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(v);
  });

  const categoryNames = Object.keys(grouped).sort(); // sort category list alphabetically

  let dropdownHtml =  buildVariableDropdown();  

  categoryNames.forEach(cat => {
    const sortedVars = grouped[cat].sort((a, b) => a.display_name.localeCompare(b.display_name));
    dropdownHtml += `<optgroup label="${cat.charAt(0).toUpperCase() + cat.slice(1)}">`;
    sortedVars.forEach(v => {
      dropdownHtml += `<option value="${v.name}">${v.display_name}</option>`;
    });
    dropdownHtml += `</optgroup>`;
  });

  // ✅ Include all previously saved user-defined variables
  if (userDefinedVariables.length > 0) {
    const sortedUserVars = [...userDefinedVariables].sort((a, b) => a.name.localeCompare(b.name));
    dropdownHtml += `<optgroup label="User Defined">`;
    sortedUserVars.forEach(v => {
      dropdownHtml += `<option value="${v.name}">${v.name}</option>`;
    });
    dropdownHtml += `</optgroup>`;
  }

  wrapper.innerHTML = `
    <div class="field box p-2 has-background-light">
      <button class="delete is-small is-pulled-right"
        onclick="this.closest('.expression-item').remove(); validateExpressionBuilder(${index})">
      </button>
      <select class="inline-variable-dropdown"
        onchange="renderInlineVariableParams(this, ${index}); validateExpressionBuilder(${index})"
        style="width: 200px;">
        ${dropdownHtml}
      </select>
      <div class="parameters mt-1"></div>
    </div>`;

  target.appendChild(wrapper);
  validateExpressionBuilder(index);

  // ✅ Initialize Select2 with category formatting
  setTimeout(() => {
    const $dropdown = $(wrapper).find('.inline-variable-dropdown');
    $dropdown.select2({
      width: '200px',
      placeholder: "Search variable",
      allowClear: true,
      templateResult: formatDropdownItem
    });
  }, 0);
}

function addExpressionOperator(index) {
  const target = document.getElementById(`expression_builder_${index}`);
  const wrapper = document.createElement('div');
  wrapper.classList.add('expression-item');

  wrapper.innerHTML = `
    <div class="field box p-2 has-background-light">
      <button class="delete is-small is-pulled-right" onclick="this.closest('.expression-item').remove(); validateExpressionBuilder(${index})"></button>
      <div class="select">
        <select onchange="validateExpressionBuilder(${index})">
          <option value="+">+</option>
          <option value="-">-</option>
          <option value="*">*</option>
          <option value="/">/</option>
          <option value="%">%</option>
        </select>
      </div>
    </div>`;
  target.appendChild(wrapper);
  validateExpressionBuilder(index);
}

function addExpressionValue(index) {
  const target = document.getElementById(`expression_builder_${index}`);
  const wrapper = document.createElement('div');
  wrapper.classList.add('expression-item');

  wrapper.innerHTML = `
    <div class="field box p-2 has-background-light">
      <button class="delete is-small is-pulled-right" onclick="this.closest('.expression-item').remove(); validateExpressionBuilder(${index})"></button>
      <input type="number" step="any" placeholder="e.g. 1.5" class="input is-small" oninput="validateExpressionBuilder(${index})">
    </div>`;
  target.appendChild(wrapper);
  validateExpressionBuilder(index);
}

function validateExpressionBuilder(index) {
  const target = document.getElementById(`expression_builder_${index}`);
  const items = target.querySelectorAll('.expression-item');
  const errors = [];

  const statusIcon = document.getElementById(`constant_status_${index}`);
  const previewEl = document.getElementById(`const_preview_${index}`);

  const parts = [];

  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const isVariable = item.querySelector('.inline-variable-dropdown');
    const isOperator = item.querySelector('select') && !isVariable;
    const isValue = item.querySelector('input') && !isVariable;

    // Validation Rules
    if (i === 0 && isOperator) {
      errors.push("❌ Expression cannot start with an operator.");
    }
    if (i === items.length - 1 && isOperator) {
      errors.push("❌ Expression cannot end with an operator.");
    }

    if ((isValue || isVariable) && i < items.length - 1) {
      const nextItem = items[i + 1];
      const nextIsValue = nextItem.querySelector('input') && !nextItem.querySelector('.inline-variable-dropdown');
      const nextIsVariable = nextItem.querySelector('.inline-variable-dropdown');
      if (nextIsValue || nextIsVariable) {
        errors.push("❌ Operator required between two values/variables.");
      }
    }

    // Build preview part
    if (isVariable) {
      const varName = isVariable.value;
      const paramEls = item.querySelectorAll('.parameters input, .parameters select');
      const paramParts = [];

      paramEls.forEach(p => {
        const key = p.name.split('_').pop();
        if (p.value) {
          paramParts.push(`${key}=${p.value}`);
        }
      });

      parts.push(`${varName}(${paramParts.join(', ')})`);
    } else if (isOperator) {
      parts.push(item.querySelector('select').value);
    } else if (isValue) {
      const val = item.querySelector('input').value;
      if (val) parts.push(val);
    }
  }

  // Formula Preview
  if (previewEl) {
    previewEl.textContent = parts.join(' ');
  }

  // Validation Icon
  if (statusIcon) {
    statusIcon.innerHTML = errors.length === 0
      ? `<i class="has-text-success">✅</i>`
      : `<i class="has-text-danger">❌</i>`;
  }

  // Error Box
  let errorBox = document.getElementById(`expr_error_box_${index}`);
  if (!errorBox) {
    errorBox = document.createElement('div');
    errorBox.id = `expr_error_box_${index}`;
    errorBox.className = "notification is-danger is-light mt-2";
    target.parentElement.appendChild(errorBox);
  }

  errorBox.style.display = errors.length ? 'block' : 'none';
  errorBox.innerHTML = errors.length
    ? `<strong>Validation Error:</strong><ul>${errors.map(e => `<li>${e}</li>`).join('')}</ul>`
    : '';
}

function updateUserVariableHiddenJSON(index) {
  const box = document.getElementById(`user_constant_box_${index}`);
  const container = document.getElementById(`expression_builder_${index}`);
  const nameInput = box.querySelector(`input[name="user_constant_name_${index}"]`);
  const name = nameInput?.value?.trim();

  if (!name) return;

  const items = container.querySelectorAll('.expression-item');
  const expression = [];

  items.forEach(item => {
    const isVariable = item.querySelector('.inline-variable-dropdown');
    const isOperator = item.querySelector('select') && !isVariable;
    const isValue = item.querySelector('input') && !isVariable;

    if (isVariable) {
      const varName = isVariable.value;
      const params = [];
      const paramEls = item.querySelectorAll('.parameters input, .parameters select');
      paramEls.forEach(p => {
        const key = p.name.split('_').pop();
        if (p.value) params.push({ key, value: p.value });
      });
      expression.push({ type: 'variable', name: varName, parameters: params });
    } else if (isOperator) {
      const value = item.querySelector('select').value;
      expression.push({ type: 'operator', value });
    } else if (isValue) {
      const value = item.querySelector('input').value;
      expression.push({ type: 'value', value });
    }
  });

  // Update hidden input
  const hidden = getHiddenInput(index);
    if (hidden) hidden.value = JSON.stringify({ name, expression });

}

function saveUserConstant(index) {
  const box = document.getElementById(`user_constant_box_${index}`);
  const container = document.getElementById(`expression_builder_${index}`);
  const nameInput = box.querySelector(`input[name="user_constant_name_${index}"]`);
  const name = nameInput?.value?.trim();
  const closeBtn = document.getElementById(`user_variable_close_${index}`);
  const originalName = nameInput.getAttribute('data-original') || name;

  if (closeBtn) closeBtn.style.display = 'none';

  // Validate name
  const allInputs = document.querySelectorAll('input[name^="user_constant_name_"]');
  let duplicate = false;
  allInputs.forEach(inp => {
    if (inp !== nameInput && inp.value.trim() === name) duplicate = true;
  });

  const existsInPredefined = userDefinedVariables.some(v => v.name === name && name !== originalName);
    const hdr = box.querySelector('.user-const-header');
    if (hdr) hdr.style.display = 'none';

  const errorText = document.getElementById(`var_name_error_${index}`);
  if (!name || (duplicate || existsInPredefined)) {
    nameInput.classList.add("is-danger");
    nameInput.title = !name ? "Variable name cannot be empty" : "Variable name already exists";
    if (errorText) {
      errorText.textContent = name ? "Variable name already exists" : "Variable name cannot be empty";
    }
    return;
  }

  nameInput.classList.remove("is-danger");
  nameInput.removeAttribute("title");
  if (errorText) errorText.textContent = "";

  // Expression builder logic
  const items = container.querySelectorAll('.expression-item');
  const expression = [];
  let formulaPreview = "";

  items.forEach(item => {
    const isVariable = item.querySelector('.inline-variable-dropdown');
    const isOperator = item.querySelector('select') && !isVariable;
    const isValue = item.querySelector('input') && !isVariable;

    if (isVariable) {
      const varName = isVariable.value;
      const params = [];
      const paramEls = item.querySelectorAll('.parameters input, .parameters select');
      paramEls.forEach(p => {
        const key = p.name.split('_').pop();
        if (p.value) params.push({ key, value: p.value });
      });
      expression.push({ type: 'variable', name: varName, parameters: params });
      formulaPreview += `${varName}(${params.map(p => `${p.key}=${p.value}`).join(', ')}) `;
    } else if (isOperator) {
      const value = item.querySelector('select').value;
      expression.push({ type: 'operator', value });
      formulaPreview += ` ${value} `;
    } else if (isValue) {
      const value = item.querySelector('input').value;
      expression.push({ type: 'value', value });
      formulaPreview += `${value} `;
    }
  });

  // Update hidden input
  const hiddenInput = getHiddenInput(index);
if (hiddenInput) {
  hiddenInput.value = JSON.stringify({ name, expression });
}

  // UI updates
  const preview = document.getElementById(`const_preview_${index}`);
  if (preview) preview.style.display = 'none';

  const fieldBlocks = box.querySelectorAll('.field, .buttons, .expression_builder, .udv-header');
  fieldBlocks.forEach(el => el.style.display = 'none');

  const oldBtn = box.querySelector("button[onclick^='saveUserConstant']");
  if (oldBtn) oldBtn.remove();

  const summaryLine = document.createElement('div');
  summaryLine.id = `user_constant_summary_${index}`;
  summaryLine.className = 'mt-2 p-2 has-background-light has-text-weight-semibold';
  summaryLine.innerHTML = `<span class="has-text-grey-dark">${name} = ${formulaPreview.trim()}</span>`;
  box.appendChild(summaryLine);

  const actionWrapper = document.createElement("div");
  actionWrapper.className = "buttons mt-2";
  actionWrapper.id = `edit_delete_controls_${index}`;
  actionWrapper.innerHTML = `
    <button type="button" class="button is-small is-warning" onclick="editUserConstant(${index})">✏️</button>
    <button type="button" class="button is-small is-danger" onclick="removeUserConstant(${index})">🗑️</button>
  `;
  box.appendChild(actionWrapper);

  // Update global registry
  userDefinedVariables = userDefinedVariables.filter(v => v.name !== originalName);
  userDefinedVariables.push({ name, expression });
document.dispatchEvent(new CustomEvent('udv:changed', { detail: { action: 'save', name } }));
  // Update dropdowns
 // 🆕 Update all dropdowns with the latest user-defined variable list
const allDropdowns = document.querySelectorAll('.inline-variable-dropdown');
allDropdowns.forEach(dd => {
  const currentVal = dd.value; // preserve selected value
  dd.innerHTML = getAllVariableOptionsHTML();
  $(dd).val(currentVal).trigger('change.select2');  // update Select2
});

  // Persist to backend
 

  // Track saved name
  nameInput.setAttribute("data-original", name);
}


function ensureSaveButton(index) {
  const box = document.getElementById(`user_constant_box_${index}`);
  if (!box) return;
  const footer = box.querySelector(`#editor_footer_${index}`);
  if (!footer) return;

  let saveBtn = footer.querySelector("button[data-role='save-user-constant']");
  if (!saveBtn) {
    saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'button is-small is-success';
    saveBtn.textContent = '💾 Save Variable';
    saveBtn.setAttribute('data-role', 'save-user-constant');
    saveBtn.setAttribute('onclick', `saveUserConstant(${index})`);
    footer.appendChild(saveBtn);
  } else {
    // if it exists but was hidden, show it
    saveBtn.style.display = '';
  }
}
function editUserConstant(index) {
  const box = document.getElementById(`user_constant_box_${index}`);
  if (!box) return;

  // read saved JSON for this box
  const hidden = box.querySelector(`#user_constant_input_${index}`);
  let saved = null;
  try { saved = hidden ? JSON.parse(hidden.value) : null; } catch (e) {}

  // remove summary & edit/delete controls
  box.querySelector(`#user_constant_summary_${index}`)?.remove();
  box.querySelector(`#edit_delete_controls_${index}`)?.remove();

  // ensure header exists (don’t reuse expression-item deletes!)
  let header = box.querySelector('.udv-header');
  if (!header) {
    header = document.createElement('div');
    header.className = 'udv-header is-flex is-justify-content-space-between is-align-items-center mb-2';
    header.innerHTML = `<strong>Variable Definition</strong>`;
    const topClose = document.createElement('button');
    topClose.className = 'delete udv-close';
    topClose.type = 'button';
    topClose.onclick = function(){ removeUserConstant(index); };
    header.appendChild(topClose);
    box.insertBefore(header, box.firstChild);
  } else {
    header.style.display = '';
  }

  // ensure name field exists
  let nameField = box.querySelector(`input[name="user_constant_name_${index}"]`);
  if (!nameField) {
    const field = document.createElement('div');
    field.className = 'field';
    field.innerHTML = `
      <label class="label">Variable Name</label>
      <input class="input" name="user_constant_name_${index}" placeholder="e.g., Variable1" data-original="">
      <p id="var_name_error_${index}" class="help is-danger" style="display:none;"></p>
    `;
    box.insertBefore(field, header.nextSibling);
    nameField = field.querySelector('input');
  }
  nameField.parentElement.style.display = '';

  // ensure builder exists
  let builder = box.querySelector(`#expression_builder_${index}`);
  if (!builder) {
    builder = document.createElement('div');
    builder.id = `expression_builder_${index}`;
    builder.className = 'expression_builder is-flex is-align-items-center is-flex-wrap-wrap mb-3';
    box.appendChild(builder);
  } else {
    builder.style.display = '';
  }

  // ensure toolbar exists
  let toolbar = box.querySelector('.udv-toolbar');
  if (!toolbar) {
    toolbar = document.createElement('div');
    toolbar.className = 'buttons udv-toolbar mb-2';
    toolbar.innerHTML = `
      <button type="button" class="button is-small is-primary" onclick="addExpressionVariable(${index})">➕ Variable</button>
      <button type="button" class="button is-small is-info" onclick="addExpressionOperator(${index})">➕ Operator</button>
      <button type="button" class="button is-small is-link" onclick="addExpressionValue(${index})">➕ Value</button>
    `;
    box.appendChild(toolbar);
  } else {
    toolbar.style.display = '';
  }

  // ensure save button exists
  let saveBtn = box.querySelector(`button[onclick^="saveUserConstant(${index})"]`);
  if (!saveBtn) {
    saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'button is-small is-success';
    saveBtn.textContent = '💾 Save Variable';
    saveBtn.setAttribute('onclick', `saveUserConstant(${index})`);
    box.appendChild(saveBtn);
  } else {
    saveBtn.style.display = '';
  }

  // set name & original
  if (saved?.name) {
    nameField.value = saved.name;
    nameField.setAttribute('data-original', saved.name);
  }

  // rebuild expression UI from saved
  builder.innerHTML = '';
  if (Array.isArray(saved?.expression)) {
    populateExpressionBuilderFromSaved(index, saved.expression);
  }

  // validate & refresh hidden JSON
  validateExpressionBuilder(index);
  if (typeof updateUserVariableHiddenJSON === 'function') {
    updateUserVariableHiddenJSON(index);
  }
}


function ensureVariableEditor(index) {
  const box = document.getElementById(`user_constant_box_${index}`);
  if (!box) return {};

  // Name field
  let nameField = box.querySelector(`input[name="user_constant_name_${index}"]`);
  // Builder
  let builder   = box.querySelector(`#expression_builder_${index}`);
  // Action buttons (add var/op/value)
  let actions   = box.querySelector(`#editor_actions_${index}`);
  // Footer to host Save
  let footer    = box.querySelector(`#editor_footer_${index}`);

  // Create if missing (e.g., preloaded summary-only box)
  if (!nameField || !builder || !actions || !footer) {
    const frag = document.createElement('div');
    frag.innerHTML = `
      <div class="field">
        <label class="label">Variable Name</label>
        <input class="input" name="user_constant_name_${index}" placeholder="e.g., Variable1" data-original="">
        <p id="var_name_error_${index}" class="help is-danger" style="display:none;"></p>
      </div>

      <div id="expression_builder_${index}" class="expression_builder is-flex is-align-items-center is-flex-wrap-wrap mb-3"></div>
      <p id="const_preview_${index}" class="is-size-7 has-text-grey mt-1 ml-1"></p>

      <div class="buttons mb-2" id="editor_actions_${index}">
        <button type="button" class="button is-small is-primary" onclick="addExpressionVariable(${index})">➕ Variable</button>
        <button type="button" class="button is-small is-info"    onclick="addExpressionOperator(${index})">➕ Operator</button>
        <button type="button" class="button is-small is-link"    onclick="addExpressionValue(${index})">➕ Value</button>
      </div>

      <div class="mt-2" id="editor_footer_${index}"></div>
    `;
    box.appendChild(frag);

    nameField = box.querySelector(`input[name="user_constant_name_${index}"]`);
    builder   = box.querySelector(`#expression_builder_${index}`);
    actions   = box.querySelector(`#editor_actions_${index}`);
    footer    = box.querySelector(`#editor_footer_${index}`);
  }

  // Make editor visible
  [nameField.closest('.field'), builder, actions, footer].forEach(el => { if (el) el.style.display = ''; });

  return { nameInput: nameField, builder, actions, footer };
}

function populateExpressionBuilderFromSaved(index, expression) {
  const target = document.getElementById(`expression_builder_${index}`);
  if (!target) return;

  const toParamList = (params) => {
    if (!params) return [];
    if (Array.isArray(params)) return params; // [{key,value}]
    return Object.entries(params).map(([key, value]) => ({ key, value }));
  };

  expression.forEach(part => {
    if (part.type === 'variable') {
      const wrap = document.createElement('div');
      wrap.className = 'expression-item';
      wrap.innerHTML = `
        <div class="field box p-2 has-background-light">
          <button class="delete is-small is-pulled-right"
            onclick="this.closest('.expression-item').remove(); validateExpressionBuilder(${index})"></button>
          <select class="inline-variable-dropdown" style="width:200px;"
            onchange="renderInlineVariableParams(this, ${index}); validateExpressionBuilder(${index})">
            ${getAllVariableOptionsHTML()}
          </select>
          <div class="parameters mt-1"></div>
        </div>
      `;
      target.appendChild(wrap);

      const dd = wrap.querySelector('.inline-variable-dropdown');
      if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
        $(dd).select2({ width: '200px', placeholder: 'Search variable', allowClear: true, templateResult: formatDropdownItem });
      }

      const varName = part.name || part.value || '';
      dd.value = varName;
      if (typeof $ !== 'undefined' && $.fn && $.fn.select2) $(dd).val(varName).trigger('change.select2');

      // render params (⚠️ MUST pass index so symbol ID is unique)
      renderInlineVariableParams(dd, index);

      // prefill param values (works for both array/object shapes)
      const params = toParamList(part.parameters);
      params.forEach(({ key, value }) => {
        if (!key) return;
        if (String(key).toLowerCase() === 'symbol') {
          const sym = wrap.querySelector('.parameters .symbol-dropdown');
          if (sym && value != null) {
            sym.id = sym.id || `sym_${index}_${Math.random().toString(36).slice(2,8)}`;
            initSelect2(`#${sym.id}`, 'Select symbol');
            if (![...sym.options].some(o => o.value === value)) {
              sym.add(new Option(value, value, true, true));
            }
            if (typeof $ !== 'undefined') $(sym).val(value).trigger('change.select2');
          }
        } else {
          const inp = wrap.querySelector(`.parameters [name$="${key}"]`);
          if (inp) inp.value = value ?? '';
        }
      });
    }

    else if (part.type === 'operator') {
      const wrap = document.createElement('div');
      wrap.className = 'expression-item';
      wrap.innerHTML = `
        <div class="field box p-2 has-background-light">
          <button class="delete is-small is-pulled-right"
            onclick="this.closest('.expression-item').remove(); validateExpressionBuilder(${index})"></button>
          <div class="select">
            <select onchange="validateExpressionBuilder(${index})">
              <option value="+">+</option>
              <option value="-">-</option>
              <option value="*">*</option>
              <option value="/">/</option>
              <option value="%">%</option>
            </select>
          </div>
        </div>
      `;
      target.appendChild(wrap);
      wrap.querySelector('select').value = part.value || '+';
    }

    else if (part.type === 'value') {
      const wrap = document.createElement('div');
      wrap.className = 'expression-item';
      wrap.innerHTML = `
        <div class="field box p-2 has-background-light">
          <button class="delete is-small is-pulled-right"
            onclick="this.closest('.expression-item').remove(); validateExpressionBuilder(${index})"></button>
          <input type="number" step="any" placeholder="e.g. 1.5" class="input is-small"
            oninput="validateExpressionBuilder(${index})">
        </div>
      `;
      target.appendChild(wrap);
      wrap.querySelector('input').value = part.value ?? '';
    }
  });

  validateExpressionBuilder(index);
}

function removeUserConstant(index) {
  const box = document.getElementById(`user_constant_box_${index}`);
  if (!box) return;

  // --- 1) Resolve the variable name (input → hidden JSON → summary text)
  let name = '';
  const nameInput = box.querySelector(`input[name="user_constant_name_${index}"]`);
  if (nameInput) name = nameInput.value.trim();

  if (!name) {
    const hidden = document.getElementById(`user_constant_input_${index}`);
    if (hidden && hidden.value) {
      try {
        const parsed = JSON.parse(hidden.value);
        if (parsed && parsed.name) name = String(parsed.name).trim();
      } catch (e) {
        console.warn("Invalid hidden JSON for user var", index, e);
      }
    }
  }

  if (!name) {
    const summary = box.querySelector(`#user_constant_summary_${index}`);
    if (summary) {
      const txt = (summary.textContent || '');
      const eq = txt.indexOf('=');
      if (eq > -1) name = txt.slice(0, eq).trim();
    }
  }

  if (!name) {
    console.warn(`❌ Could not resolve variable name for deletion (index ${index})`);
    return;
  }

  // --- 2) Usage checks (other UDVs, LHS, RHS)
  let usedInOtherUserVars = false;
  let usedAsLHS = false;
  let usedAsRHS = false;

  // other UDVs
  for (const v of (userDefinedVariables || [])) {
    if (v.name !== name) {
      try {
        const exprString = JSON.stringify(v.expression || []);
        if (exprString.includes(`"${name}"`)) { usedInOtherUserVars = true; break; }
      } catch { /* ignore */ }
    }
  }

  // in condition rows
  usedAsLHS = Array.from(document.querySelectorAll(".condition-variable"))
                   .some(select => select.value === name);
  usedAsRHS = Array.from(document.querySelectorAll(".rhs-variable-dropdown"))
                   .some(select => select.value === name);

  if (usedInOtherUserVars || usedAsLHS || usedAsRHS) {
    // You already have a modal; feel free to swap alert() for showVarInUseModal()
    let msg = `⚠️ Cannot delete "${name}" because it is used `;
    if (usedInOtherUserVars) msg += `in another user-defined variable.`;
    else if (usedAsLHS)      msg += `in a condition row (LHS).`;
    else if (usedAsRHS)      msg += `in a condition row (RHS).`;
    alert(msg);
    return;
  }

  // --- 3) Remove DOM (also removes the hidden input inside the box)
  box.remove();

  // --- 4) Update global registry
  userDefinedVariables = (userDefinedVariables || []).filter(v => v.name !== name);
document.dispatchEvent(new CustomEvent('udv:changed', { detail: { action: 'save', name } }));

  // --- 5) Refresh EVERY variable dropdown using your helper
  document.querySelectorAll('.inline-variable-dropdown, .condition-variable, .rhs-variable-dropdown')
    .forEach(dd => {
      const was = dd.value;
      dd.innerHTML = getAllVariableOptionsHTML();

      // If the deleted var was selected, clear it; otherwise preserve selection
      const nextVal = (was === name) ? '' : was;

      if (typeof $ !== 'undefined' && $.fn && $.fn.select2 && $(dd).hasClass('select2-hidden-accessible')) {
        $(dd).val(nextVal).trigger('change.select2');
      } else {
        dd.value = nextVal;
        dd.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });

}

function preloadUserDefinedVariables() {
  const container = document.getElementById("userConstantsContainer");
  container.innerHTML = "";

  if (!Array.isArray(userDefinedVariables)) return;

  userDefinedVariables.forEach((variable, index) => {
    // 1) Create the outer box
    const box = document.createElement("div");
    box.className = "box mb-3";
    box.id = `user_constant_box_${index}`;

    // 2) Hidden input to keep the JSON for form submit & edit
    const hiddenInput = document.createElement("input");
    hiddenInput.type = "hidden";
    hiddenInput.name = `user_variable_json_${index}`;
    hiddenInput.id   = `user_constant_input_${index}`;
    hiddenInput.value = JSON.stringify(variable);
    box.appendChild(hiddenInput);

    // 3) Summary line: "Name = expression"
    const summaryLine = document.createElement("div");
    summaryLine.id        = `user_constant_summary_${index}`;
    summaryLine.className = "mt-2 p-2 has-background-light has-text-weight-semibold";
    summaryLine.innerHTML = `
      <span class="has-text-grey-dark">
        ${variable.name} = ${formatExpressionText(variable.expression)}
      </span>
    `;
    box.appendChild(summaryLine);

    // 4) Action buttons: Edit & Delete
    const actionWrapper = document.createElement("div");
    actionWrapper.id        = `edit_delete_controls_${index}`;
    actionWrapper.className = "buttons mt-2";
    actionWrapper.innerHTML = `
      <button type="button" class="button is-small is-warning"
              onclick="editUserConstant(${index})">✏️</button>
      <button type="button" class="button is-small is-danger"
              onclick="removeUserConstant(${index})">🗑️</button>
    `;
    box.appendChild(actionWrapper);

    // 5) Append to container
    container.appendChild(box);

    // 6) Make this variable available in all condition dropdowns
    document.querySelectorAll('.condition-variable, .inline-variable-dropdown')
      .forEach(dd => {
        if (![...dd.options].some(o => o.value === variable.name)) {
          const opt = document.createElement("option");
          opt.value   = variable.name;
          opt.textContent = variable.name;
          dd.appendChild(opt);
        }
      });
  });
  document.dispatchEvent(new CustomEvent('udv:changed', { detail: { source: 'preload' } }));
}

function formatExpressionText(expression) {
  return expression.map(item => {
    if (item.type === "variable") {
      const paramStr = (item.parameters || []).map(p => `${p.key}=${p.value}`).join(', ');
      return `${item.name}(${paramStr})`;
    } else if (item.type === "operator") {
      return ` ${item.value} `;
    } else if (item.type === "value") {
      return item.value;
    } else {
      return '';
    }
  }).join('');
}
