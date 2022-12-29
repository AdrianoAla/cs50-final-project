# This or That? [Video](https://youtu.be/VLUHXXl5t_I)

I finished the CS50x with this project!! Got 100% on it too!

# Project Description

"This or That?" is a web app built with Flask that allows users to create polls to predict events, whether they be sporting events, political events, or predicting trends in the entertainment and tech industry, you can vote on anything! The app uses an SQLite3 database, which we learned how to use in the course, to store user accounts, polls and their options, votes, and notifications.

The app required me to apply many of the skills that I learned in the CS50. Skills such as HTML, basic CSS, Javascript, Python, Flask, SQL databases, password hashing and Jinja syntax. But I also had to do a lot of research into topics like flexbox for CSS, animations for CSS, and project managments with tools like Python virtual environments.

The project saw me making many interesting design choices for the sake of readability, one of which was made fairly late in the development of the project, and it was to not use `SELECT *` in my SQL queries. I simply found that selecting every column in a table simply had no advantage, but it had many disadvantages. Take the following query

`SELECT * FROM users WHERE id = 2;`

All we know from this query is that we are selecting every property of the users table for user number two, but this does not tell us what the users table contains. Knowing some things we can assume it has a username and a password column, but we cannot assume much more.

`SELECT id, username, friend_count FROM users WHERE id = 2;`

However when given this query, it is much easier to infer what we are going to do with this data, maybe we are visiting the profile of this user on some social media app. Avoiding the use of `SELECT *` has the additional benefit of allowing us to ignore columns that are unnecessary in the context of the query, and thus makes tuple unpacking much easier.

# Features
- Fully fledged authentication state system.
    - Registration page prompts user for a username, a password, and a confirmation of the password.
    - Login page asks user for username and password to authenticate themselves.
    - Logout route clears user session and redirects them to the login page.
    - Simple implementation of protected routes
- Reactive navigation bar.
    - Changes based on authentication state to display links to login or to log out.
    - Minimalistic design using flex to evenly space out links.
- Homepage
    - Simple display of the user's current level and the amount of polls they must solve to advance to the next level.
    - Shows all of the users polls that they've created so they can access them easily.
    - Minimalistic inbox which allows users to recieve updates on all of their predictions, whether they were correct, incorrect, or if the poll was deleted.
- Search
    - Allows users to search for polls by name, category, or both using get parameters. 
    - Displays results by most recent by using the polls' id.
- Create
    - Simple descriptive UI to create polls, using flex to organize all the inputs in a pretty and sensible manner.
    - Back end checks to make sure no fields are left empty, which could cause errors.
- Error page
    - Sizeable royalty free graphic that allows the user to instantly notice they made an error.
    - Link to return to the homepage is included.


# Files

##  database.db
This file is the main database file used by the program. It's schema is as follows:

- `Users`
    - ID
    - Username
    - Password Hash
    - Polls Participated
    - Successful Predictions
- `Polls`
    - ID
    - ID of Creator (references `Users`)
    - Question
    - Category
    - Expires (UNIX timestamp representing when the poll should close)
    - Over (either `1` or `0`, represents if the poll was manually closed)
- `Poll Options`
    - ID
    - ID of Poll (references `Polls`)
    - Option Text
- `Poll Votes`
    - ID 
    - ID of Voter (references `Users`)
    - ID of Poll (references `Polls`)
    - ID of Option (references `Poll Options`)

## app.py
This is the main application file, containing all the functions that respond to GET and POST requests from the user. It also does all the database interactions using the SQLite3 Python module from PyPi. Finally, app.py uses the `werkzeug.security` package to create and validate password hashes during the `login` and `register` functions.

## templates/layout.html
This page contains the HTML elements that are required in each page, alongside Jinja code to allow for the layout to be modified in every page according to the page's needs.

## templates/login.html and templates/register.html
These pages contain simple HTTP POST forms that allow the user to sign into their accounts or to create new ones securely.

## templates/index.html
The index page is the central page of the application, containing information about the user, like their level, the number of polls they must complete to advance to the next level, their polls, and their notifications, all of which are displayed in a linear and non-cluttered way.

## templates/poll.html

This page is used to display polls and allow users to vote on them, the page cleanly displays the poll's name, category and the amount of votes that have been cast on it. It then provides the ability for users to vote on the poll, after which users will be unable to vote again.

The page also provides the creator of the poll with the ability to delete the poll or to end it if they know the results.

## templates/user.html

This page allows you to see information about users on the website, such as their level and the polls that they have created.

## templates/search.html

This page provides a simple but intuitive search form, where users can provide a query and a category of poll that they are looking for, and they will find results from the SQL database based on the `LIKE` operator.

## templates/error.html

This page is used to render errors to the user, it displays a large error graphic and explains clearly to the user what caused the error. The page then contains a link to return to the homepage.

## templates/create.html

This page displays a simple HTTP POST form that allows authenticated users to create polls by adding a title, category, expiry date and time and as many options as they need by using Javascript to create more option inputs.
