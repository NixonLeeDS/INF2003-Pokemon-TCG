// Run: mongosh "mongodb://127.0.0.1:27017/inf2003_pokemon" --file scripts/mongo_evidence.js
// Read-only evidence. Capture database version and counts with the results.
print('MongoDB version: ' + db.version());
print('Documents: ' + db.card_details.countDocuments({}));
printjson(db.card_details.getIndexes());
printjson(db.card_details.aggregate([
  {$unwind: '$types'},
  {$project: {type: '$types', attacks: {$size: {$ifNull: ['$attacks', []]}}}},
  {$group: {_id: '$type', cards: {$sum: 1}, averageAttacks: {$avg: '$attacks'}}},
  {$sort: {cards: -1, _id: 1}}
]).toArray());
// Deduplicate weakness types per card so counts mean cards, not array entries.
printjson(db.card_details.aggregate([
  {$project: {weaknessTypes: {$setUnion: [{$ifNull: ['$weaknesses.type', []]}, []]}}},
  {$unwind: '$weaknessTypes'},
  {$group: {_id: '$weaknessTypes', cards: {$sum: 1}}},
  {$sort: {cards: -1, _id: 1}}
]).toArray());
printjson(db.card_details.find({types: 'Fire'}, {name: 1, types: 1}).explain('executionStats'));
