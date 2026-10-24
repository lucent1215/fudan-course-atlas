CREATE TABLE `review_files` (
	`id` text PRIMARY KEY NOT NULL,
	`review_id` text NOT NULL,
	`object_key` text NOT NULL,
	`name` text NOT NULL,
	`mime` text NOT NULL,
	`size` integer NOT NULL
);
--> statement-breakpoint
CREATE INDEX `files_review` ON `review_files` (`review_id`);--> statement-breakpoint
CREATE TABLE `community_reviews` (
	`id` text PRIMARY KEY NOT NULL,
	`course_id` text NOT NULL,
	`author_id` text NOT NULL,
	`teacher` text NOT NULL,
	`term` text NOT NULL,
	`class_type` text NOT NULL,
	`nickname` text NOT NULL,
	`learning` text NOT NULL,
	`workload` text NOT NULL,
	`assessment` text NOT NULL,
	`grading` text NOT NULL,
	`overall` text NOT NULL,
	`grade` text NOT NULL,
	`hours` integer,
	`created_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `reviews_course_date` ON `community_reviews` (`course_id`,`created_at`);--> statement-breakpoint
CREATE INDEX `reviews_author_date` ON `community_reviews` (`author_id`,`created_at`);