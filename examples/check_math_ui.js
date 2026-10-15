// Run through playwright-cli run-code --filename=examples/check_math_ui.js.
// Creates and deletes only its own temporary course. Requires AI to be disabled.
async page => {
  const base = 'http://127.0.0.1:8765/api/';
  const call = async (method, path, data) => {
    const response = await page.request.fetch(base + path, {method, data});
    if (!response.ok()) throw new Error(`${method} ${path}: ${response.status()}`);
    return response.status() === 204 ? null : response.json();
  };
  if ((await call('GET', 'status/')).generation_enabled) throw new Error('Refuse a possible AI request in this browser check');
  const course = await call('POST', 'courses/', {name: '[Verification] Local LaTeX browser checks'});
  const question = String.raw`Math regression: simplify \(\frac{1}{2}\).`;
  const answer = String.raw`\[\frac{1}{2}=0.5\]`;
  const edited = String.raw`\[\frac{d}{dx}x^3=3x^2\]`;
  const notes = String.raw`The square of two is four. Use \(x=2\), then \[x^2=4\]. The price $20 stays currency.`;
  const report = {};
  try {
    let source = await call('POST', 'sources/', {course: course.id, title: 'Local math check notes', text: notes});
    const deadline = Date.now() + 30000;
    while (source.status !== 'ready') {
      if (source.status === 'error' || Date.now() > deadline) throw new Error('Source ingestion did not finish');
      await page.waitForTimeout(250);
      source = await call('GET', `sources/${source.id}/`);
    }
    const card = await call('POST', 'study-items/', {course: course.id, kind: 'flashcard', title: question, data: {answer}, completed: false});
    await call('POST', 'study-items/', {course: course.id, kind: 'quiz', title: String.raw`Find \(\det\begin{bmatrix}1&2\\3&4\end{bmatrix}\).`, data: {options: [String.raw`\(-2\)`, String.raw`\(2\)`], answer: String.raw`\(-2\)`}, completed: false});
    const conversations = [];
    for (const title of ['Math questions', 'Other questions']) conversations.push(await call('POST', 'conversations/', {course: course.id, title}));
    await page.setViewportSize({width: 1440, height: 1000});
    await page.goto(`http://127.0.0.1:5173/?course=${course.id}`);
    await page.getByRole('button', {name: 'Preview math', exact: true}).click();
    const preview = page.getByRole('region', {name: 'Formatted page text'});
    await preview.locator('math').first().waitFor();
    report.source_equations = await preview.locator('math').count();
    if (report.source_equations !== 2 || await preview.locator('.math-invalid').count()) throw new Error('Source math preview failed');
    await page.getByRole('button', {name: 'Edit text', exact: true}).click();
    if (await page.getByRole('textbox', {name: 'Extracted page text'}).inputValue() !== notes) throw new Error('Source preview changed raw LaTeX');
    await page.getByRole('button', {name: 'Study tools', exact: true}).click();
    let study = page.locator('.study-card').filter({hasText: 'Math regression'});
    await study.locator('math').first().waitFor();
    if (await study.locator('.flash-answer math').count()) throw new Error('Answer leaked before reveal');
    await study.getByRole('button', {name: 'Reveal answer', exact: true}).click();
    if (await study.locator('.flash-answer math').count() !== 1) throw new Error('Flashcard answer was not typeset');
    report.flashcard_front_and_back = true;
    await study.getByRole('button', {name: 'Edit card', exact: true}).click();
    const field = study.getByRole('textbox', {name: 'Answer', exact: true});
    if (await field.inputValue() !== answer) throw new Error('Edit did not preserve raw answer');
    await field.fill(edited);
    await study.getByText('Preview math', {exact: true}).click();
    const saved = page.waitForResponse(response => response.url().endsWith(`/study-items/${card.id}/`) && response.request().method() === 'PATCH');
    await study.getByRole('button', {name: 'Save', exact: true}).click();
    if (!(await saved).ok()) throw new Error('Flashcard save failed');
    await page.reload();
    await page.getByRole('button', {name: 'Study tools', exact: true}).click();
    study = page.locator('.study-card').filter({hasText: 'Math regression'});
    await study.getByRole('button', {name: 'Reveal answer', exact: true}).click();
    await study.locator('.flash-answer math').waitFor();
    const record = await call('GET', `study-items/${card.id}/`);
    if (record.data.answer !== edited || record.title !== question) throw new Error('Math edit/reload lost the original source');
    report.edit_reload_preserved_tex = true;
    await page.screenshot({path: 'artifacts/math-workspace/flashcard-verified.png'});
    await page.setViewportSize({width: 390, height: 844});
    if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) throw new Error('Math caused horizontal page overflow');
    report.mobile_no_page_overflow = true;
    await page.setViewportSize({width: 1440, height: 1000});
    await page.getByRole('button', {name: /^Quizzes/}).click();
    await page.locator('.quiz-options button').first().click();
    if (await page.locator('.quiz-options button.correct math').count() !== 1) throw new Error('Typeset quiz choice did not preserve answer identity');
    report.quiz_equation_and_choice = true;
    const content = String.raw`Explain the square \(x^2\) in the notes.`;
    await page.getByRole('textbox', {name: 'Question', exact: true}).fill(content);
    await page.getByRole('button', {name: 'Save question', exact: true}).click();
    const panel = page.locator('.chat-panel');
    await panel.locator('.message.user math').waitFor();
    await panel.locator('.message-list[aria-busy="false"]').waitFor();
    await page.getByRole('textbox', {name: 'Question', exact: true}).fill('Another saved question');
    if (!(await page.getByRole('button', {name: 'Save question', exact: true}).isEnabled()) || await panel.locator('.assistant-working').count()) throw new Error('Paused chat locked its composer');
    await page.getByRole('combobox', {name: 'Conversation', exact: true}).selectOption({label: 'Other questions'});
    await panel.locator('.chat-empty').waitFor();
    if (await panel.locator('.message').count() || !(await page.getByRole('button', {name: 'Save question', exact: true}).isEnabled())) throw new Error('Conversation state leaked');
    const messages = await call('GET', `conversations/${conversations[0].id}/messages/`);
    if (!messages.some(message => message.role === 'user' && message.content === content)) throw new Error('Chat math source was not saved exactly');
    report.math_chat_and_paused_recovery = true;
    return report;
  } finally {
    await call('DELETE', `courses/${course.id}/`);
    await page.setViewportSize({width: 1440, height: 1000});
  }
}
