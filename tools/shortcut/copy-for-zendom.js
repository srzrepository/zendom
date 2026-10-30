// "Copy for zen·dom" — paste into the Shortcuts action "Run JavaScript on Web Page".
// Reads the recipe from the page open in your Safari (where you're signed in), nothing else.
var blocks = [];
document.querySelectorAll('script[type="application/ld+json"]').forEach(function (s) {
  try { blocks.push(JSON.parse(s.textContent)); } catch (e) {}
});
var hasRecipe = JSON.stringify(blocks).indexOf('"Recipe"') !== -1;
if (hasRecipe) {
  completion(JSON.stringify({ zendom: 1, url: location.href, recipe: blocks }));
} else {
  var main = document.querySelector('main, article') || document.body;
  completion(document.title + "\n\n" + main.innerText.slice(0, 20000));
}
