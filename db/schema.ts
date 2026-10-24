// Intentionally empty by default.
// Add Drizzle tables here when the site actually needs a database.
// See examples/d1/db/schema.ts for an opt-in example.
import { sqliteTable, text, integer, index } from 'drizzle-orm/sqlite-core';
export const reviews = sqliteTable('community_reviews', {
 id: text('id').primaryKey(), courseId:text('course_id').notNull(), authorId:text('author_id').notNull(),
 teacher:text('teacher').notNull(), term:text('term').notNull(), classType:text('class_type').notNull(),
 nickname:text('nickname').notNull(), learning:text('learning').notNull(), workload:text('workload').notNull(),
 assessment:text('assessment').notNull(), grading:text('grading').notNull(), overall:text('overall').notNull(),
 grade:text('grade').notNull(), hours:integer('hours'), createdAt:text('created_at').notNull(),
 kind:text('kind').notNull().default('review'),
}, t=>[index('reviews_course_date').on(t.courseId,t.createdAt),index('reviews_author_date').on(t.authorId,t.createdAt)]);
export const files=sqliteTable('review_files',{
 id:text('id').primaryKey(),reviewId:text('review_id').notNull(),objectKey:text('object_key').notNull(),
 name:text('name').notNull(),mime:text('mime').notNull(),size:integer('size').notNull()
},t=>[index('files_review').on(t.reviewId)]);
