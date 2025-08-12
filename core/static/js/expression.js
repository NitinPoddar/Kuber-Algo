function addUserDefinedVariable() {
  const container = document.getElementById('userConstantsContainer');
  const index = container.children.length;

  const box = document.createElement('div');
  box.classList.add('box', 'mb-3');
  box.id = `user_constant_box_${index}`;
  box.innerHTML = `
    <div class="is-flex is-justify-content-space-between is-align-items-center mb-2">
      <strong>Variable Definition</strong>
      <div class="is-flex is-align-items-center">
        <span id="constant_status_${index}" class="icon is-small mr-2"></span>
        <button type="button" class="delete" 
+              onclick="this.closest('.box').remove()">
+      </button>
      </div>
    </div>

    <div class="field">
      <label class="label">Variable Name</label>
      <input class="input" name="user_constant_name_${index}" placeholder="e.g., Variable1" data-original-name="">
      <p id="var_name_error_${index}" class="help is-danger" style="display:none;"></p>
    </div>

    <div id="expression_builder_${index}" class="is-flex is-align-items-center is-flex-wrap-wrap mb-3"></div>
    <p id="const_preview_${index}" class="is-size-7 has-text-grey mt-1 ml-1"></p>

    <div class="buttons mb-2">
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
  let hiddenInput = document.getElementById(`user_constant_input_${index}`);
  if (!hiddenInput) {
    hiddenInput = document.createElement("input");
    hiddenInput.type = "hidden";
    hiddenInput.name = `user_variable_json_${index}`;
    hiddenInput.id = `user_constant_input_${index}`;
    document.getElementById("algoForm").appendChild(hiddenInput);
  }

  hiddenInput.value = JSON.stringify({ name, expression });
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
  let hiddenInput = document.getElementById(`user_constant_input_${index}`);
  if (!hiddenInput) {
    hiddenInput = document.createElement("input");
    hiddenInput.type = "hidden";
    hiddenInput.name = `user_variable_json_${index}`;
    hiddenInput.id = `user_constant_input_${index}`;
    document.getElementById("algoForm").appendChild(hiddenInput);
  }
  hiddenInput.value = JSON.stringify({ name, expression });

  // UI updates
  const preview = document.getElementById(`const_preview_${index}`);
  if (preview) preview.style.display = 'none';

  const fieldBlocks = box.querySelectorAll('.field, .buttons, .expression_builder');
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

function editUserConstant(index) {
  const box = document.getElementById(`user_constant_box_${index}`);
  const summary = document.getElementById(`user_constant_summary_${index}`);
  const controls = document.getElementById(`edit_delete_controls_${index}`);
  const preview = document.getElementById(`const_preview_${index}`);
  const closeBtn = document.getElementById(`user_variable_close_${index}`);

  if (summary) summary.remove();
  if (controls) controls.remove();
  if (preview) preview.style.display = 'none';
  if (closeBtn) closeBtn.style.display = 'inline-block';

  const allFields = box.querySelectorAll('.field, .expression_builder, .buttons');
  allFields.forEach(el => el.style.display = '');

  const oldBtn = box.querySelector("button[onclick^='saveUserConstant']");
  if (oldBtn) oldBtn.remove();

  const saveBtn = document.createElement('button');
  saveBtn.type = 'button';
  saveBtn.className = 'button is-small is-success';
  saveBtn.textContent = '💾 Save Variable';
  saveBtn.setAttribute('onclick', `saveUserConstant(${index})`);
  box.appendChild(saveBtn);

  const nameInput = box.querySelector(`input[name="user_constant_name_${index}"]`);
  const originalName = nameInput.value.trim();
  nameInput.setAttribute('data-original', originalName);

  // Error box
  let errorText = document.getElementById(`var_name_error_${index}`);
  if (!errorText) {
    errorText = document.createElement("p");
    errorText.id = `var_name_error_${index}`;
    errorText.className = "help is-danger";
    nameInput.parentElement.appendChild(errorText);
  }

  // Revalidation
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

    const existsInPredefined = userDefinedVariables.some(v => v.name === name && name !== originalName);
    const isSameAsOriginal = name === originalName;

    if (!name) {
      nameInput.classList.add("is-danger");
      nameInput.title = "Variable name cannot be empty";
      errorText.textContent = "Variable name cannot be empty";
      saveBtn.disabled = true;
    } else if ((duplicate || existsInPredefined) && !isSameAsOriginal) {
      nameInput.classList.add("is-danger");
      nameInput.title = "Variable name already exists";
      errorText.textContent = "Variable name already exists";
      saveBtn.disabled = true;
    } else {
      nameInput.classList.remove("is-danger");
      nameInput.removeAttribute("title");
      errorText.textContent = "";
      saveBtn.disabled = false;
    }
  });

  nameInput.dispatchEvent(new Event("input"));  // Trigger validation immediately
}

function removeUserConstant(index) {
  const box = document.getElementById(`user_constant_box_${index}`);
  const nameInput = box.querySelector(`input[name="user_constant_name_${index}"]`);
  const name = nameInput?.value?.trim();
  if (!name) return;

  let usedInOtherUserVars = false;
  let usedAsLHS = false;
  let usedAsRHS = false;

  // 🔍 1. Check if variable is used in other user-defined variables
  for (let v of userDefinedVariables) {
    if (v.name !== name) {
      const exprString = JSON.stringify(v.expression);
      if (exprString.includes(`"${name}"`)) {
        usedInOtherUserVars = true;
        break;
      }
    }
  }

  // 🔍 2. Check if variable is used in LHS of condition rows
  const lhsSelects = document.querySelectorAll(".condition-variable");
  usedAsLHS = Array.from(lhsSelects).some(select => select.value === name);

  // 🔍 3. Check if variable is used in RHS of condition rows
  const rhsSelects = document.querySelectorAll(".rhs-variable-dropdown");
  usedAsRHS = Array.from(rhsSelects).some(select => select.value === name);

  // 🚫 If used anywhere, prevent deletion
  if (usedInOtherUserVars || usedAsLHS || usedAsRHS) {
    let msg = `⚠️ Cannot delete "${name}" because it is used `;
    if (usedInOtherUserVars) msg += `in another user-defined variable.`;
    else if (usedAsLHS) msg += `as a variable in a condition row (LHS).`;
    else if (usedAsRHS) msg += `as a variable in a condition row (RHS).`;
    alert(msg);
    return;
  }

  // ✅ 1. Remove from DOM
  box?.remove();

  // ✅ 2. Remove from global registry
  userDefinedVariables = userDefinedVariables.filter(v => v.name !== name);

  // ✅ 3. Remove from all condition dropdowns
  const dropdowns = document.querySelectorAll(".condition-variable, .rhs-variable-dropdown");
  dropdowns.forEach(dd => {
    const options = dd.querySelectorAll("option");
    options.forEach(opt => {
      if (opt.value === name) opt.remove();
    });
  });

  // ✅ 4. Remove from sessionStorage
  const saved = sessionStorage.getItem("userDefinedVariables");
  if (saved) {
    try {
      const parsed = JSON.parse(saved).filter(v => v.name !== name);
      sessionStorage.setItem("userDefinedVariables", JSON.stringify(parsed));
    } catch (err) {
      console.warn("⚠️ Session storage cleanup failed:", err);
    }
  }

  // ✅ 5. Inform backend (optional)
  fetch('/api/user_variable/delete/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
    },
    body: JSON.stringify({ name })
  }).then(res => {
    if (!res.ok) {
      console.error(`❌ Failed to delete ${name} from DB`);
    }
  }).catch(err => {
    console.error('❌ AJAX Delete Error:', err);
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
}


function updateUserVariableHiddenJSON(index) {
  const container = document.getElementById(`expression_builder_${index}`);
  const hiddenInput = document.getElementById(`user_constant_input_${index}`);

  if (!container || !hiddenInput) {
    console.warn(`🚨 Could not find container or hidden input for variable ${index}`);
    return;
  }

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

  hiddenInput.value = JSON.stringify({ name: document.querySelector(`input[name='user_constant_name_${index}']`).value.trim(), expression });
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
