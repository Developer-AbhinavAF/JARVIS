import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  parseJarvis,
  parseInline,
  extractResponseText,
  isAllowedColor,
  isSafeUrl,
} from '../src/lib/jarvisProtocol.ts';

const tag = (name: string) => '<' + name + '>';
const close = (name: string) => '<' + '/' + name + '>';

test('parses full structured response into ordered blocks', () => {
  const input = [
    tag('think') + 'Let me reason about this carefully.' + close('think'),
    tag('analyze') + 'User wants a summary.' + close('analyze'),
    tag('response') + '**Here is the answer.**' + close('response'),
  ].join('\n');
  const r = parseJarvis(input);
  assert.equal(r.structured, true);
  assert.equal(r.truncated, false);
  assert.deepEqual(
    r.blocks.map((b) => b.kind),
    ['think', 'analyze', 'response']
  );
  assert.equal(r.blocks[0].kind === 'think' && r.blocks[0].raw, 'Let me reason about this carefully.');
  assert.equal(r.blocks[2].kind === 'response' && r.blocks[2].raw, '**Here is the answer.**');
});

test('code block carries language attribute', () => {
  const r = parseJarvis(
    tag('response') + 'Done.' + close('response') + '<code lang="python">print(1)</code>'
  );
  const code = r.blocks.find((b) => b.kind === 'code');
  assert.ok(code);
  assert.equal(code.language, 'python');
  assert.equal(code.code, 'print(1)');
  assert.equal(code.closed, true);
});

test('canvas block extracted with title', () => {
  const r = parseJarvis('<canvas title="Report"># Title\n\nBody</canvas>');
  const canvas = r.blocks.find((b) => b.kind === 'canvas');
  assert.ok(canvas);
  assert.equal(canvas.title, 'Report');
  assert.ok(canvas.raw.includes('# Title'));
});

test('image block from content URL and from src attr', () => {
  const a = parseJarvis(tag('image') + 'https://example.com/a.png' + close('image'));
  const b = parseJarvis('<image src="https://example.com/b.jpg" title="Photo" />');
  assert.equal(a.blocks[0].kind === 'image' && a.blocks[0].src, 'https://example.com/a.png');
  assert.equal(b.blocks[0].kind === 'image' && b.blocks[0].src, 'https://example.com/b.jpg');
});

test('plain markdown text has no structured blocks', () => {
  const r = parseJarvis('Hello, how are you? **bold** and `code`');
  assert.equal(r.structured, false);
  assert.equal(r.blocks.length, 1);
  assert.equal(r.blocks[0].kind, 'text');
});

test('unclosed block mid-stream marks truncated and keeps content', () => {
  const r = parseJarvis(tag('think') + 'It looks like the answer\n');
  assert.equal(r.truncated, true);
  assert.ok(r.blocks.some((b) => b.kind === 'think' && !b.closed && b.raw.includes('It looks')));
});

test('partial open tag at end is literal pending completion', () => {
  const r = parseJarvis('Hello <ana');
  assert.equal(r.truncated, true);
  assert.equal(r.structured, false);
  assert.equal(r.blocks[0].kind, 'text');
});

test('unclosed block at end becomes truncated without dropping text', () => {
  const r = parseJarvis(tag('response') + 'Here is my answer so far...');
  assert.equal(r.truncated, true);
  const resp = r.blocks.find((b) => b.kind === 'response');
  assert.ok(resp && resp.raw === 'Here is my answer so far...');
});

test('script/iframe/unknown tags stay literal text', () => {
  const r = parseJarvis('<script>alert(1)</script> <iframe src="x"></iframe>');
  assert.equal(r.structured, false);
  assert.equal(r.blocks[0].kind, 'text');
  assert.ok(r.blocks[0].raw.includes('<script>alert(1)</script>'));
});

test('javascript: URLs are not safe', () => {
  assert.equal(isSafeUrl('https://ok.example/photo.jpg'), true);
  assert.equal(isSafeUrl('javascript:alert(1)'), false);
  assert.equal(isSafeUrl('data:text/html,x'), false);
  assert.equal(isSafeUrl('https://ok.example/x" onerror="alert(1)'), false);
});

test('image block with unsafe url yields src but renderer gates it', () => {
  const r = parseJarvis(tag('image') + 'javascript:alert(1)' + close('image'));
  const img = r.blocks[0];
  assert.equal(img.kind, 'image');
  assert.equal(isSafeUrl(img.src), false);
});

test('stray closing tag is kept literal, does not crash', () => {
  const r = parseJarvis(close('response') + ' leading text');
  assert.equal(r.structured, false);
  assert.ok(r.blocks[0].raw.includes(close('response')));
});

test('inline bold italic underline strikethrough', () => {
  const nodes = parseInline(
    '<b>B</b> <i>I</i> <u>U</u> <lthrough>S</lthrough>'
  );
  const types = nodes
    .filter((n) => n.type !== 'text')
    .map((n) => (n.type === 'color' ? 'color' : n.type));
  assert.deepEqual(types, ['bold', 'italic', 'underline', 'strikethrough']);
});

test('color with whitelist name and hex', () => {
  assert.equal(isAllowedColor('red'), true);
  assert.equal(isAllowedColor('#0f0'), true);
  assert.equal(isAllowedColor('#ff00ff'), true);
  assert.equal(isAllowedColor('toString'), false);
  assert.equal(isAllowedColor('javascript:'), false);
  assert.equal(isAllowedColor('#zzz'), false);

  const good = parseInline('<color name="red">x</color>');
  const bad = parseInline('<color name="expression">x</color>');
  assert.equal(good[0].type === 'color' && good[0].color, 'red');
  assert.equal(bad[0].type, 'text');
});

test('nested inline formatting', () => {
  const nodes = parseInline('<b>bold <color name="blue">blue-bold</color></b> tail');
  const bold = nodes.find((n) => n.type === 'bold');
  assert.ok(bold && bold.type === 'bold');
  const color = bold.children.find((n) => n.type === 'color');
  assert.ok(color && color.type === 'color' && color.color === 'blue');
});

test('mismatched close is literal, stack unwinds at end', () => {
  const nodes = parseInline('<b>oops</i>');
  let hasBold = false;
  const walk = (list: unknown) => {
    for (const n of list as Array<{ type: string; children?: unknown }>) {
      if (n.type !== 'text') {
        hasBold = true;
        walk(n.children);
      }
    }
  };
  walk(nodes);
  assert.equal(hasBold, false);
  const text = nodes.map((n) => (n.type === 'text' ? n.text : '')).join('');
  assert.ok(text.includes('oops'));
});

test('plain angle brackets stay text', () => {
  const nodes = parseInline('a < b and c < d > e');
  assert.equal(nodes[0].type, 'text');
});

test('extractResponseText prefers response block', () => {
  const input =
    tag('saved') + 'note' + close('saved') +
    tag('response') + '**Answer**: `x = 1`' + close('response');
  assert.equal(extractResponseText(input), 'Answer: x = 1');
});

test('extractResponseText falls back to text blocks', () => {
  assert.equal(extractResponseText('plain **hello**'), 'plain hello');
});

test('extractResponseText strips list markers and headings', () => {
  const text = extractResponseText(
    tag('response') + '# Title\n- one\n- two' + close('response')
  );
  assert.ok(!text.includes('#'));
  assert.ok(!text.includes('-'));
});