# Explanation files

Every `*.json` file in `code-atlas/explain/` is merged, in file-name order. Split them however suits the project; one file per area works well (`01-api.json`, `02-web.json`). Each file can hold any of the sections below. `scan.mjs` never rewrites them, except that `--stamp` adds `hash` fields and moves an entry when its box was renamed but its code did not change.

See `examples/explain-example.json` for a complete small example.

## nodes: what each box is and does

```json
{ "nodes": {
  "api/orders.go#formatOrder": { "what": "Turns an order into the short label shown in lists.", "does": "Orders over 10 are labelled 'big', the rest 'small'.", "example": "An order of 20 becomes 'big'." },
  "area:api": { "what": "The part of the shop that answers web requests about orders.", "does": "main.go starts a web server; handlers/ has one function per address." }
} }
```

- `what`: one sentence, what it is for. Shown large.
- `does`: two to four sentences, how it does it.
- `example`: optional. A concrete input and output, or a real situation.
- `hash`: added by `--stamp`. When the code changes, the box shows "code changed".
- Use `[[term]]` to link a glossary word, and backticks for code.

## glossary

```json
{ "glossary": { "handler": "A function the web server runs when a request arrives at one address." } }
```

## tours: guided walkthroughs

```json
{ "tours": [{ "title": "Someone opens the orders page", "intro": "From the click to the list", "steps": [
  { "id": "api/main.go#main", "text": "The server starts and listens on port 8080." },
  { "id": "api/handlers/orders.go#ListOrders", "text": "A request for /orders arrives; ListOrders answers it." }
] }] }
```

## beginner: jobs, wire labels, inputs and outputs, Play steps

```json
{ "beginner": {
  "roles": { "api/main.go#main": "boss", "api/handlers/orders.go#formatOrder": "helper" },
  "io": { "api/handlers/orders.go#formatOrder": { "in": "One order, like {ID: 2, Total: 20}.", "out": "'big' or 'small'.", "to": "to label an order", "tag": "label it" } },
  "wires": { "api/handlers/orders.go#ListOrders>api/handlers/orders.go#loadOrders": { "short": "1 · get orders", "text": "ListOrders first asks loadOrders for every order." } },
  "plays": { "area:api": { "title": "One request, start to finish", "steps": [
    { "id": "api/main.go", "text": "main.go starts the server." },
    { "id": "api/handlers/orders.go", "from": "api/main.go", "text": "Requests for /orders go to orders.go." }
  ] } }
} }
```

- **roles:** one of boss, worker, helper, ingredients or decoration. These are worked out automatically (code that runs by itself is a boss, anything used by 3 or more others is a helper, styles are decoration, content is ingredients); set roles only to correct them.
- **io:**
  - `in` is what it takes in. Use a real-looking example.
  - `out` is what it gives back.
  - `to` is the purpose phrase used in sentences ("Main asks Format Order **to label an order**").
  - `tag` is a 2 to 4 word wire label.
  - Write these for every box you explain. Wire sentences, automatic Play captions and the Story view are all built from them.
- **wires:** optional hand-written labels for single wires, keyed `from>to` using the boxes as drawn on that level.
- **plays:** hand-written Play walkthroughs for a level (an area, group or file). `from` names the box that hands over to this step, so its wire lights up. Files with two or more functions get an automatic Play from the call order, so hand-write them only where order or meaning needs telling.

## story: hand-written stories

Every level gets a generated story. Hand-write one (key `overview` for the top level, or any box id) when you want characters and dialogue:

```json
{ "story": { "overview": {
  "title": "Shop Town", "town": "Everything in shop", "intro": "The whole shop as a small town.",
  "cast": [
   { "key": "area:api", "id": "area:api", "name": "Market Street", "short": "Market St", "job": "boss", "hello": "I answer every order question." },
   { "key": "web", "name": "The Internet", "job": "ingredients", "hello": "Where customers come from." }
  ],
  "scenes": [
   { "from": "web", "to": "area:api", "say": "How many orders do I have?", "parcel": "GET /orders", "reply": "Two!", "back": "a list of 2 orders", "caption": "A customer's browser asks the API for orders.", "file": "api/main.go", "line": 10 }
  ],
  "quiz": [{ "q": "Who answers order questions?", "options": ["The Internet", "Market Street"], "answer": 1 }]
} } }
```

- **cast:** `key` is used by scenes. `id` (optional) links to a box, so the code name shows under the sign, and if it has a door you can click in. `job` picks the badge icon.
- **scenes:**
  - `say` and `reply` go in the speech bubbles.
  - `parcel` and `back` are the labels on the envelopes going out and coming back.
  - `caption` is one short sentence.
  - `file` and `line` choose the code shown in "Peek at the real code".
  - A scene with the same `from` and `to` is someone talking alone.
- Keep captions under about 14 words, and each bubble to one sentence.
