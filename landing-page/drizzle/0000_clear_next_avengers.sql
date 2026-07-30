CREATE TABLE `interests` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`email` text NOT NULL,
	`consented_at` text NOT NULL,
	`consent_version` text NOT NULL,
	`source` text NOT NULL,
	`status` text DEFAULT 'active' NOT NULL,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `interests_email_unique` ON `interests` (`email`);--> statement-breakpoint
CREATE INDEX `interests_status_idx` ON `interests` (`status`);