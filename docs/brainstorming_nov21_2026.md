look, monitoring and inspection system should be easy to use and understand. 
- user should be able to find multiple submissions of the same establishment or entity and see how it was before and how it is now. 
- admin should be able to manage odk central accounts from mandi backend. create accounts, and manage which user has access to which forms from here. 
- 


hey, I want to hvae this:
- admin logins. 
- creates establishment types with name in pashto, persain and english. example types can be hospital, pharmacy, medicine factory.
- then, admin creats a user, and specify which establishment types he has acess, some users to only one types, others to multiple types. 
- the user, then creates xls form, and uploads it, the xls form is created with a title, description, and who created it, creation date, etc are stored. 
- the admin might then create some other users. the admin then decide which users have access to which xlsforms. the users from the ODK central are also created from here. no need to create separate account on odk central. 
- the users then connect their mobile app using the qr code. and then, go to field and collect data. when submit the data, it is stored on odk central. 
- a user which clicks on establishment can see the checklists and submissions for that establishment. when click the submission, it should show a clean detail page of the submission. should use the xlsform to know how to properly structure the data into sections, etc. 
- when click on xlsForm, its detail page should also show the form and its different fields and other detials in a proper and understandable format. 
- the xlsForm can be configured to allow user select one of the entities saved on the mandi backend. when such, when a user searches an establishment, and selects it, it should then see the name, type of that establishment and move format. user should be able to even create an xls form where first question is about establishment type, and then, when user selects establishment type, select or search of that establishment is displayed on the collection app. 

- i think i will need to use entities feature of odk for establishment. i should be able to use a list of establishments of only one type. or maybe a form where it first ask establishment type, and then showing list of only that establishment. 
