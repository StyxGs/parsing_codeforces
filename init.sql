create table tasks
(
    id serial primary key,
    task_name character varying(150),
    number character varying(30) not null unique,
    number_solved integer default 0,
    difficulty integer,
    link  character varying(350) not null
);

create table topic
(
    id serial primary key,
    topic_name character varying(250) unique
);

create table tasks_topic
(
    id bigserial primary key,
    task_number character varying(30) not null,
    topic_id integer not null references topic,
    unique (task_number, topic_id)
);

create table users
(
    id serial primary key,
    tg_id integer not null unique
);

create table users_tasks
(
    id bigserial primary key,
    user_id integer not null references users,
    task_id integer not null references tasks
)