# UniWare ER Diagram

```mermaid
erDiagram
	USER ||--o{ EQUIPMENT : provides
	USER ||--o{ BORROW_REQUEST : borrows
	USER ||--o{ BORROW_REQUEST : decides
	USER ||--o{ CHECKOUT : hands_over
	USER ||--o{ EQUIPMENT_SUSPENSION_NOTICE : receives
	USER ||--o{ CONSENT_RECORD : gives
	CATEGORY ||--o{ EQUIPMENT : classifies
	LOCATION ||--o{ EQUIPMENT : houses
	EQUIPMENT ||--o{ BORROW_REQUEST : "requested as"
	BORROW_REQUEST ||--o| CHECKOUT : "handover record"
	EQUIPMENT ||--o{ EQUIPMENT_SUSPENSION_NOTICE : concerns

	USER {
		uuid id PK
		string email UK "USERNAME_FIELD, chula.ac.th only"
		string first_name
		string last_name
		string department "blank allowed"
		bool is_admin
		bool is_provider
		bool is_borrower
		bool is_active
		bool is_staff
		bool is_superuser
		string account_status "ACTIVE|SUSPENDED"
		datetime date_joined
	}
	CONSENT_RECORD {
		uuid id PK
		uuid user_id FK
		string consent_version
		string consent_text_hash
		datetime granted_at
		string ip_address
		string user_agent
	}
	CATEGORY {
		uuid id PK
		string name UK
	}
	LOCATION {
		uuid id PK
		string name UK
	}
	EQUIPMENT {
		uuid id PK
		string asset_id UK
		string name
		string photo_original "slot 1 storage path"
		string photo_preview "slot 1 storage path"
		string photo_2_original "slot 2 storage path"
		string photo_2_preview "slot 2 storage path"
		string photo_3_original "slot 3 storage path"
		string photo_3_preview "slot 3 storage path"
		string model
		text description
		uuid provider_id FK
		uuid category_id FK
		uuid location_id FK
		string status "AVAILABLE|RESERVED|CHECKED_OUT|MAINTENANCE|ARCHIVED|DISABLED"
		datetime archived_at
		datetime disabled_at
		text disabled_reason
		bool admin_suspended
		text admin_suspension_reason
		datetime admin_suspended_at
		datetime created_at
		datetime updated_at
	}
	BORROW_REQUEST {
		uuid id PK
		uuid borrower_id FK
		uuid equipment_id FK
		date pickup_date "inclusive: first day of possession"
		date due_date "exclusive: handover-back day"
		text purpose
		string status "PENDING|APPROVED|REJECTED|CANCELLED|CHECKED_OUT|RETURNED|COMPLETED"
		text decision_reason
		uuid decided_by_id FK
		datetime decided_at
		text return_condition
		datetime returned_at
		string photo_original "return photo storage path"
		string photo_preview "return photo storage path"
	}
	CHECKOUT {
		bigint id PK
		uuid request_id FK, UK
		uuid handover_person_id FK
		datetime checkout_at
	}
	EQUIPMENT_SUSPENSION_NOTICE {
		bigint id PK
		uuid recipient_id FK
		uuid equipment_id FK
		string message
		datetime created_at
	}
```

A checked-out borrow request represents an active loan; there is no separate Loan model. A checkout record stores the handover actor and time. Legacy requests may have no checkout record. `COMPLETED` is a legacy request status; new returns use `RETURNED`.

Photo fields contain private storage paths, not image data. Equipment supports three original/preview pairs; a return can have one pair. Empty strings indicate missing photos. `is_suspended` and `suspension_reason` are calculated properties, not database columns. The diagram omits Django's built-in authentication and session tables.
